#!/usr/bin/env python3
import argparse
import logging
import math
import os
from pathlib import Path
import sys

import itk
import monai
from monai.transforms import Compose, EnsureChannelFirstd, LoadImaged, ScaleIntensityd, ToTensord
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error, r2_score
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import wandb

existing_count = 0
missing_count = 0
predict_hd_data_root = 'P:/PREDICTHD_BIDS_DEFACE/'

regression_count = 3  # first 3 values are overall QA, SNR and CNR
artifacts = [
    'normal_variants',
    'lesions',
    'full_brain_coverage',
    'misalignment',
    'swap_wraparound',
    'ghosting_motion',
    'inhomogeneity',
    'susceptibility_metal',
    'flow_artifact',
    'truncation_artifact',
]

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
    print(f'{count} images in prefix {path_prefix}')


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
        # print(f'Exists: {fileName}')
        existing_count += 1
        return True
    else:
        # print(f'Missing: {fileName}')
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
    print(f'Existing files: {existing_count}, non-existent files: {missing_count}')
    return df


def verify_images(data_frame):
    all_ok = True
    for index, row in data_frame.iterrows():
        try:
            dim = get_image_dimension(row.file_path)
            if dim == (0, 0, 0):
                print(f'{index}: size of {row.file_path} is zero')
                all_ok = False
        except Exception as e:
            print(f'{index}: there is some problem with: {row.file_path}:\n{e}')
            all_ok = False
    return all_ok


class TiledClassifier(monai.networks.nets.Classifier):
    def forward(self, inputs):
        # split the input image into tiles and run each tile through NN
        results = []
        z_tile_size = self.in_shape[0]
        y_tile_size = self.in_shape[1]
        x_tile_size = self.in_shape[2]
        z_size = inputs.shape[2]
        y_size = inputs.shape[3]
        x_size = inputs.shape[4]
        z_steps = math.ceil(z_size / z_tile_size)
        y_steps = math.ceil(y_size / y_tile_size)
        x_steps = math.ceil(x_size / x_tile_size)
        for k in range(z_steps):
            k_start = round(k * (z_size - z_tile_size) / max(1, z_steps - 1))
            for j in range(y_steps):
                j_start = round(j * (y_size - y_tile_size) / max(1, y_steps - 1))
                for i in range(x_steps):
                    i_start = round(i * (x_size - x_tile_size) / max(1, x_steps - 1))

                    # use slicing operator to make a tile
                    tile = inputs[
                        :,
                        :,
                        k_start : k_start + z_tile_size,
                        j_start : j_start + y_tile_size,
                        i_start : i_start + x_tile_size,
                    ]

                    # check if the tile is smaller than our NN input
                    x_pad = max(0, x_tile_size - x_size)
                    y_pad = max(0, y_tile_size - y_size)
                    z_pad = max(0, z_tile_size - z_size)

                    if x_pad + y_pad + z_pad > 0:  # we need to pad
                        tile = torch.nn.functional.pad(
                            tile, (0, x_pad, 0, y_pad, 0, z_pad), 'replicate'
                        )

                    results.append(super().forward(tile))

        # TODO: do something smarter than mean here
        average = torch.mean(torch.stack(results), dim=0)
        return average


def evaluate_model(model, data_loader, device, writer, epoch, run_name):
    model.eval()
    y_pred = []
    y_pred_continuous = []
    y_true = []
    with torch.no_grad():
        metric_count = 0
        for val_data in data_loader:
            inputs = val_data['img'].to(device)
            info = val_data['info'].to(device)
            outputs = model(inputs)

            y_true.extend(info[..., 0].cpu().tolist())
            y = outputs[..., 0].cpu().tolist()
            y_pred_continuous.extend(y)
            y = [int(round(y[t])) for t in range(len(y))]
            y = [max(0, min(y[t], 10)) for t in range(len(y))]  # clamp to 0 - 10 range
            y_pred.extend(y)

            metric_count += len(info)
            print('.', end='', flush=True)
            if metric_count % 100 == 0:
                print('', flush=True)

        if writer is not None:  # this is not a one-off case
            print('\n' + run_name + '_confusion_matrix:')
            print(confusion_matrix(y_true, y_pred))
            print(classification_report(y_true, y_pred))

            metric = mean_squared_error(y_true, y_pred_continuous, squared=False)
            writer.add_scalar(run_name + '_RMSE', metric, epoch + 1)
            wandb.log({run_name + '_RMSE': metric})
            metric = r2_score(y_true, y_pred_continuous)
            writer.add_scalar(run_name + '_R2', metric, epoch + 1)
            wandb.log({run_name + '_R2': metric})
            return metric
        else:
            return outputs


def evaluate1(model_path, image_path):
    itk_reader = monai.data.ITKReader()
    # Define transforms for image
    train_transforms = Compose(
        [
            LoadImaged(keys=['img'], reader=itk_reader),
            EnsureChannelFirstd(keys=['img']),
            ScaleIntensityd(keys=['img']),
            ToTensord(keys=['img']),
        ]
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    evaluation_ds = monai.data.Dataset(
        data=[
            {
                'img': image_path,
                'info': torch.FloatTensor([0] * (regression_count + len(artifacts))),
            }
        ],
        transform=train_transforms,
    )
    evaluation_loader = DataLoader(
        evaluation_ds, batch_size=1, num_workers=1, pin_memory=torch.cuda.is_available()
    )

    model = TiledClassifier(
        in_shape=(1, 64, 64, 64),
        classes=regression_count + len(artifacts),
        channels=(2, 4, 8, 16),
        strides=(
            2,
            2,
            2,
            2,
        ),
    )
    model.to(device)

    model.load_state_dict(torch.load(model_path))
    print(f'Loaded NN model from file "{model_path}"')

    tensor_output = evaluate_model(model, evaluation_loader, device, None, 0, 'evaluate1')
    result = tensor_output.cpu().tolist()[0]
    print(f'Network output: {result}')
    print(f'Overall quality of {image_path}, on 0-10 scale: {result[0]:.1f}')


class CombinedLoss(torch.nn.Module):
    def __init__(self, binary_class_weights, focal_loss=monai.losses.FocalLoss()):
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

        snr_out = output[..., 1]
        snr_target = target[..., 1]
        snr_loss = torch.mean((snr_out - snr_target) ** 2)

        cnr_out = output[..., 2]
        cnr_target = target[..., 2]
        cnr_loss = torch.mean((cnr_out - cnr_target) ** 2)

        # overall QA is more important than SNR and CNR
        loss = 10 * qa_loss + snr_loss + cnr_loss

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
    if value:
        return 1
    elif not value:
        return 0
    else:  # NaN
        return -1


def train_and_save_model(df, count_train, save_path, num_epochs, val_interval, only_evaluate):
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

            row_targets = [row.overall_qa_assessment, row.snr, row.cnr]
            for i, artifact in enumerate(artifacts):
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
        {'img': img, 'info': info}
        for img, info in zip(images[:count_train], ground_truth[:count_train])
    ]
    val_files = [
        {'img': img, 'info': info}
        for img, info in zip(images[-count_val:], ground_truth[-count_val:])
    ]

    itk_reader = monai.data.ITKReader()
    # Define transforms for image
    train_transforms = Compose(
        [
            LoadImaged(keys=['img'], reader=itk_reader),
            EnsureChannelFirstd(keys=['img']),
            ScaleIntensityd(keys=['img']),
            ToTensord(keys=['img']),
        ]
    )
    val_transforms = Compose(
        [
            LoadImaged(keys=['img'], reader=itk_reader),
            EnsureChannelFirstd(keys=['img']),
            ScaleIntensityd(keys=['img']),
            ToTensord(keys=['img']),
        ]
    )

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
    print(f'weights_array: {weights_array}')
    class_weights = torch.tensor(weights_array, dtype=torch.float).to(device)

    qa_weights = [1000.0 / qa_sample_counts[t] for t in range(11)]
    samples_weights = []
    for s in range(count_train):
        weight = qa_weights[int(regression_targets[s][0])]
        samples_weights.append(weight)

    samples_weight = torch.from_numpy(np.array(samples_weights)).double()
    sampler = torch.utils.data.WeightedRandomSampler(samples_weight, count_train)

    # create a training data loader
    train_ds = monai.data.Dataset(data=train_files, transform=train_transforms)
    train_loader = DataLoader(
        train_ds, batch_size=1, sampler=sampler, num_workers=4, pin_memory=torch.cuda.is_available()
    )

    # create a validation data loader
    val_ds = monai.data.Dataset(data=val_files, transform=val_transforms)
    val_loader = DataLoader(
        val_ds, batch_size=1, num_workers=4, pin_memory=torch.cuda.is_available()
    )

    model = TiledClassifier(
        in_shape=(1, 64, 64, 64),
        classes=regression_count + len(artifacts),
        channels=(2, 4, 8, 16),
        strides=(2, 2, 2, 2),
    )

    # # dim = 0 [20, xxx] -> [10, ...], [10, ...] on 2 GPUs
    # model = torch.nn.DataParallel(model)
    model.to(device)

    pretrained_path = os.path.join(os.getcwd(), 'pretrained.pth')
    if os.path.exists(save_path) and only_evaluate:
        model.load_state_dict(torch.load(save_path))
        print(f'Loaded NN model from file "{save_path}"')
    elif os.path.exists(pretrained_path):
        model.load_state_dict(torch.load(pretrained_path))
        print(f'Loaded NN model weights from "{pretrained_path}"')
    else:
        print('Training NN from scratch')

    loss_function = CombinedLoss(class_weights)
    wandb.config.learning_rate = 9e-5
    optimizer = torch.optim.Adam(model.parameters(), wandb.config.learning_rate)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.90)
    wandb.watch(model)

    # start a typical PyTorch training
    best_metric = float('-inf')
    best_metric_epoch = -1
    writer = SummaryWriter(log_dir=wandb.run.dir)

    if only_evaluate:
        print('Evaluating NN model on validation data')
        evaluate_model(model, val_loader, device, writer, 0, 'val')
        print('Evaluating NN model on training data')
        evaluate_model(model, train_loader, device, writer, 0, 'train')
        return sizes

    for epoch in range(num_epochs):
        print('-' * 25)
        print(f'epoch {epoch + 1}/{num_epochs}')
        model.train()
        epoch_loss = 0
        step = 0
        epoch_len = len(train_ds) // train_loader.batch_size
        print(f'epoch_len: {epoch_len}')
        y_true = []
        y_pred = []

        for batch_data in train_loader:
            step += 1
            inputs = batch_data['img'].to(device)
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
            epoch_len = len(train_ds) // train_loader.batch_size
            # print(f'{step}:{loss.item():.4f}', end=' ')
            print('.', end='', flush=True)
            if step % 100 == 0:
                print('', flush=True)  # new line
            writer.add_scalar('train_loss', loss.item(), epoch_len * epoch + step)
            wandb.log({'train_loss': loss.item()})
        epoch_loss /= step
        print(f'\nepoch {epoch + 1} average loss: {epoch_loss:.4f}')
        wandb.log({'epoch average loss': epoch_loss})
        epoch_cm = confusion_matrix(y_true, y_pred)
        print(f'confusion matrix:\n{epoch_cm}')
        wandb.log({'confusion matrix': epoch_cm})

        if (epoch + 1) % val_interval == 0:
            print('Evaluating on validation set')
            metric = evaluate_model(model, val_loader, device, writer, epoch, 'val')

            if metric >= best_metric:
                best_metric = metric
                best_metric_epoch = epoch + 1
                torch.save(model.state_dict(), save_path)
                torch.save(model.state_dict(), os.path.join(wandb.run.dir, 'miqaT1.pt'))
                print(f'saved new best metric model as {save_path}')

            print(
                'current epoch: {} current metric: {:.2f} best metric: {:.2f} at epoch {}'.format(
                    epoch + 1, metric, best_metric, best_metric_epoch
                )
            )

            scheduler.step()
            print(f'Learning rate after epoch {epoch + 1}: {optimizer.param_groups[0]["lr"]}')
            wandb.log({'learn_rate': optimizer.param_groups[0]['lr']})

    epoch_suffix = '.epoch' + str(num_epochs)
    torch.save(model.state_dict(), save_path + epoch_suffix)
    torch.save(model.state_dict(), os.path.join(wandb.run.dir, 'miqaT1.pt' + epoch_suffix))

    print(f'train completed, best_metric: {best_metric:.2f} at epoch: {best_metric_epoch}')
    writer.close()
    return sizes


def process_folds(folds_prefix, validation_fold, evaluate_only, fold_count):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    wandb.init(project='miqaT1', sync_tensorboard=True)

    folds = []
    for f in range(fold_count):
        csv_name = folds_prefix + f'{f}.csv'
        fold = pd.read_csv(csv_name)
        print(f'Verifying input data integrity of {csv_name}')
        if not verify_images(fold):
            print('Data verification failed. Exiting...')
            return
        folds.append(fold)

    df = pd.concat(folds, ignore_index=True)
    print(df)

    print(f'Using fold {validation_fold} for validation')
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

    print('Image size distribution:\n', sizes)


if __name__ == '__main__':
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
    # print(args)

    monai.config.print_config()

    if args.all:
        print(f'Training {args.nfolds} folds')
        for f in range(args.nfolds):
            process_folds(args.folds, f, False, args.nfolds)
        # evaluate all at the end, so results are easy to pick up from the log
        for f in range(args.nfolds):
            process_folds(args.folds, f, True, args.nfolds)
    elif args.folds is not None:
        process_folds(args.folds, args.vfold, args.evaluate, args.nfolds)
    elif args.modelfile is not None and args.evaluate1 is not None:
        evaluate1(args.modelfile, args.evaluate1)
    elif args.predicthd is not None:
        predict_hd_data_root = args.predicthd
        df = read_and_normalize_data_frame(
            predict_hd_data_root + r'phenotype/bids_image_qc_information.tsv'
        )
        print(df)
        full_path = Path('bids_image_qc_information-customized.csv').absolute()
        df.to_csv(full_path, index=False)
        print(f'CSV file written: {full_path}')
    elif args.ncanda is not None:
        print('Adding support for NCANDA data is a TODO')
    else:
        print('Not enough arguments specified')
        print(parser.format_help())
