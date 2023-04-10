#!/usr/bin/env python3
import argparse
import logging
import math
import os
from pathlib import Path
import random
import sys

import itk
import monai
from nn_inference import (
    artifacts,
    clamp,
    evaluate1,
    evaluate_model,
    get_itk_image_view_from_torchio_image,
    get_model,
    get_torchio_image_from_itk_image,
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

random.seed(30101983)
np.random.seed(30101983)
torch.manual_seed(30101983)
torch.use_deterministic_algorithms(True)

ghosting_motion_index = regression_count + artifacts.index('ghosting_motion')
inhomogeneity_index = regression_count + artifacts.index('inhomogeneity')


def index_of_abs_max(my_list):
    max_val = abs(my_list[0])
    max_index = 0
    for index, item in enumerate(my_list):
        abs_item = abs(item)
        if abs_item > max_val:
            max_val = abs_item
            max_index = index
    return max_index


def get_image_dimension(path, print_non_lps=False):
    image_io = itk.ImageIOFactory.CreateImageIO(path, itk.CommonEnums.IOFileMode_ReadMode)
    dim = (0, 0, 0)
    identity = True
    if image_io is not None:
        try:
            image_io.SetFileName(path)
            image_io.ReadImageInformation()
            assert image_io.GetNumberOfDimensions() == 3
            dim = (image_io.GetDimensions(0), image_io.GetDimensions(1), image_io.GetDimensions(2))
            for d in range(2):
                if index_of_abs_max(image_io.GetDirection(d)) != d:
                    identity = False
            if not identity and print_non_lps:
                print(f'Non-identity direction matrix: {path}')
        except RuntimeError:
            pass
    return dim, identity


def ncanda_construct_data_frame(ncanda_root_dir):
    df = pd.DataFrame(
        [],
        columns=[
            'participant_id',
            'series_type',
            'overall_qa_assessment',
            'file_path',
            'exists',
            'dimensions',
            'lps',
            'absent',
        ],
    )

    root = Path(ncanda_root_dir)
    root_len = len(root.parts)
    for path in root.rglob('*.nii.gz'):
        file_path = str(path)
        participant_id = path.parts[root_len + 1]
        series_type = path.parts[-1][0:-7]
        qa = 3 if path.parts[root_len] == 'unusable' else 8
        dimensions, lps = get_image_dimension(file_path, False)

        df.loc[len(df.index)] = [
            participant_id,
            series_type,
            qa,
            file_path,
            True,
            dimensions,
            lps,
            -1,
        ]

    logger.info(f'Found {df.shape[0]} files.')
    return df


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
    df['dimensions'], df['lps'] = zip(*df['file_path'].map(get_image_dimension))
    logger.info(f'Existing files: {existing_count}, non-existent files: {missing_count}')
    return df


def verify_images(data_frame):
    problem_indices = []
    for index, row in data_frame.iterrows():
        try:
            dim, _ = get_image_dimension(row.file_path, print_non_lps=False)
            if dim == (0, 0, 0):
                logger.warning(f'{index}: size of {row.file_path} is zero')
                problem_indices.append(index)
        except Exception as e:
            logger.warning(f'{index}: there is some problem with: {row.file_path}:\n{e}')
            problem_indices.append(index)

    data_frame.drop(problem_indices, inplace=True)
    return len(problem_indices)


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
        qa_loss = torch.sqrt(torch.mean((qa_out - qa_target) ** 2))

        # if we make overall QA a lot more important than individual artifacts,
        # then accuracy of the artifact predictions is very low
        # overallQA has 0-10, individual artifacts 0-1 range
        loss = 10 * qa_loss

        for i in range(self.presence_count):
            i_target = target[..., i + regression_count]
            if i_target != -1:
                i_output = output[..., i + regression_count]
                # make them required dimension (1D -> 2D)
                i_output2 = i_output.unsqueeze(0)
                i_target2 = i_target.unsqueeze(0)
                raw_loss = self.focal_loss(i_output2, i_target2)
                loss += raw_loss / self.binary_class_weights[int(i_target), i]
            # if target is -1 then ignore difference because ground truth was missing

        return loss


def convert_bool_to_int(value: bool):
    if value is True:
        return 1
    elif value is False:
        return 0
    else:  # NaN
        return -1


class CustomGhosting(torchio.transforms.RandomGhosting):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # now determine how much quality was reduced
            applied_params = transformed_subject.applied_transforms[-1][1]
            intensity = applied_params['intensity']['img']
            num_ghosts = applied_params['num_ghosts']['img']
            quality_reduction = 8 * intensity * math.log10(num_ghosts)

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)
            # it definitely has ghosting now
            transformed_subject['info'][ghosting_motion_index] = 1

            return transformed_subject


class CustomMotion(torchio.transforms.RandomMotion):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # now determine how much quality was reduced
            applied_params = transformed_subject.applied_transforms[-1][1]
            time = applied_params['times']['img']
            degrees = np.sum(np.absolute(applied_params['degrees']['img']))
            translation = np.sum(np.absolute(applied_params['translation']['img']))
            # motion in the middle of the acquisition process produces the most noticeable artifact
            quality_reduction = clamp(degrees + translation, 0, 10) * min(time, 1.0 - time)

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)
            if degrees + translation > 1:  # it definitely has motion now
                transformed_subject['info'][ghosting_motion_index] = 1

            return transformed_subject


class CustomBiasField(torchio.transforms.RandomBiasField):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # now determine how much quality was reduced
            # applied_params = transformed_subject.applied_transforms[-1][1]
            # coefficients = applied_params['coefficients']['img']
            # quality_reduction = 2 + np.linalg.norm(np.asarray(coefficients))
            quality_reduction = 4  # it is hard to assess impact on image quality

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)
            # it definitely has bias field now
            transformed_subject['info'][inhomogeneity_index] = 1

            return transformed_subject


class CustomSpike(torchio.transforms.RandomSpike):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # now determine how much quality was reduced
            applied_params = transformed_subject.applied_transforms[-1][1]
            intensity = applied_params['intensity']['img']
            # spikes_positions = applied_params['spikes_positions']['img']
            quality_reduction = 0 + 2 * intensity

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)
            # it definitely has bias field now
            transformed_subject['info'][inhomogeneity_index] = 1

            return transformed_subject


class CustomGamma(torchio.transforms.RandomGamma):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # now determine how much quality was reduced
            applied_params = transformed_subject.applied_transforms[-1][1]
            gamma = applied_params['gamma']['img'][0]
            quality_reduction = 10 * abs(1.0 - gamma)

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)

            return transformed_subject


class CustomNoise(torchio.transforms.RandomNoise):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        original_quality = subject['info'][0]
        if original_quality < 6 and len(subject.applied_transforms) == 1:  # low quality image
            return subject
        else:  # high-quality image, corrupt it
            transformed_subject = super().apply_transform(subject)

            # make sure we don't have negative intensities after adding noise
            transformed_subject.img.set_data(
                torch.clamp(transformed_subject.img.data, min=0.0, max=1.0)
            )

            # now determine how much quality was reduced
            applied_params = transformed_subject.applied_transforms[-1][1]
            std = applied_params['std']['img']
            quality_reduction = 40 * std

            # update the ground truth information
            new_quality = original_quality - quality_reduction
            transformed_subject['info'][0] = clamp(new_quality, 0, 10)

            return transformed_subject


def remove_axis_code_and_its_opposite(axis_list, index):
    axis_list.pop(index)
    if index % 2 == 0:
        axis_list.pop(index)  # the next one is here now
    else:
        axis_list.pop(index - 1)  # otherwise it is the previous
    return axis_list


class CustomReorient(
    torchio.transforms.augmentation.RandomTransform, torchio.transforms.SpatialTransform
):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        transformed_subject = subject
        itk_np_view = get_itk_image_view_from_torchio_image(transformed_subject.img)

        itk_so_enums = itk.SpatialOrientationEnums  # makes other lines shorter

        # the usual way of specifying the orientation is:
        # dicom_lps = itk_so_enums.ValidCoordinateOrientations_ITK_COORDINATE_ORIENTATION_RAI
        # but here we construct an axis code computationally, based on random orientation

        # make a list of 6 axis ends (orientations) and randomly choose 3
        axis_ends = [
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Right,
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Left,
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Posterior,
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Anterior,
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Inferior,
            itk_so_enums.CoordinateTerms_ITK_COORDINATE_Superior,
        ]

        index = random.randrange(6)
        first = axis_ends[index]
        axis_ends = remove_axis_code_and_its_opposite(axis_ends, index)
        index = random.randrange(4)
        second = axis_ends[index]
        axis_ends = remove_axis_code_and_its_opposite(axis_ends, index)
        index = random.randrange(2)
        third = axis_ends[index]

        # make local constants with humanely short names
        primary = itk_so_enums.CoordinateMajornessTerms_ITK_COORDINATE_PrimaryMinor
        secondary = itk_so_enums.CoordinateMajornessTerms_ITK_COORDINATE_SecondaryMinor
        tertiary = itk_so_enums.CoordinateMajornessTerms_ITK_COORDINATE_TertiaryMinor

        chosen_orientation = (first << primary) + (second << secondary) + (third << tertiary)

        orient_filter = itk.OrientImageFilter.New(
            itk_np_view,
            use_image_direction=True,
            desired_coordinate_orientation=chosen_orientation,
        )
        orient_filter.UpdateOutputInformation()  # computes output direction, among others

        # check whether we need to run the filter and update the pixel data
        if np.any(orient_filter.GetOutput().GetDirection() != itk_np_view.GetDirection()):
            orient_filter.Update()
            reoriented = orient_filter.GetOutput()
            transformed_subject['img'] = get_torchio_image_from_itk_image(reoriented)

        return transformed_subject


def create_train_and_test_data_loaders(df, count_train):
    images = []
    regression_targets = []
    sizes = {}
    artifact_column_indices = []
    for c in artifacts:
        if c in df:
            artifact_column_indices.append(1 + df.columns.get_loc(c))
        else:
            artifact_column_indices.append(1 + df.columns.get_loc('absent'))  # use dummy column

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

    if count_train > 0:
        weights_array = np.empty((2, class_count))
        for i in range(class_count):
            weights_array[0, i] = count0[i] / count_train
            weights_array[1, i] = count1[i] / count_train
    else:
        weights_array = np.ones((2, class_count))

    logger.info(f'weights_array: {weights_array}')
    class_weights = torch.tensor(weights_array, dtype=torch.float).to(device)

    rescale = torchio.transforms.RescaleIntensity(out_min_max=(0, 1))
    # axis_flip = torchio.transforms.RandomFlip(p=0.5, axes=(0, 1, 2))
    axis_orient = CustomReorient(p=0.5)
    ghosting = CustomGhosting(p=0.3, intensity=(0.2, 0.8))
    motion = CustomMotion(p=0.2, degrees=5.0, translation=5.0, num_transforms=1)
    inhomogeneity = CustomBiasField(p=0.1)
    spike = CustomSpike(p=0.1, num_spikes=(1, 1))
    # gamma = CustomGamma(p=0.1)  # after quick experimentation: gamma does not appear to help
    noise = CustomNoise(p=0.1)

    transforms = torchio.Compose(
        [rescale, axis_orient, ghosting, motion, inhomogeneity, spike, noise]
    )

    # create a training data loader
    train_loader = None
    if count_train > 0:
        train_ds = torchio.SubjectsDataset(train_files, transform=transforms)
        train_loader = DataLoader(
            train_ds,
            batch_size=1,
            shuffle=True,
            num_workers=4,
            pin_memory=torch.cuda.is_available(),
        )

    # create a validation data loader
    val_loader = None
    if count_val > 0:
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
        if train_loader is not None:
            logger.info('Evaluating NN model on training data')
            evaluate_model(model, train_loader, device, writer, 0, 'train')
        return sizes

    _, file_name = os.path.split(save_path)

    for epoch in range(num_epochs):
        logger.info('-' * 25)
        logger.info(f'epoch {epoch + 1}/{num_epochs}')
        model.train()
        epoch_loss = 0.0
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
                print(step, flush=True)  # new line
            writer.add_scalar('train_loss', loss.item(), epoch_len * epoch + step)
            wandb.log({'train_loss': loss.item()})
        print('')  # newline

        epoch_loss /= step
        logger.info(f'epoch {epoch + 1} average loss: {epoch_loss:.4f}')
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

    folds = []
    for f in range(fold_count):
        csv_name = folds_prefix + f'{f}.csv'
        fold = pd.read_csv(csv_name)
        print(f'Verifying input data integrity of {csv_name}')
        problem_count = verify_images(fold)
        if problem_count > 0:
            logger.error(
                f'Data verification failed. {problem_count} non-existing images were dropped'
            )
        folds.append(fold)

    df = pd.concat(folds, ignore_index=True)
    logger.info(f'\n{df}')

    logger.info(f'Using fold {validation_fold} for validation')
    vf = folds.pop(validation_fold)
    folds.append(vf)
    df = pd.concat(folds, ignore_index=True)

    # establish minimum number of optimization steps and epochs
    val_count = max(1, int(600 / df.shape[0]))
    epoch_count = max(35, int(30000 / df.shape[0]))
    epoch_count = math.ceil(epoch_count / val_count) * val_count

    wandb.init(project='miqaMix', sync_tensorboard=True)
    count_train = df.shape[0] - vf.shape[0]
    model_path = os.getcwd() + f'/models/miqaMix-val{validation_fold}.pth'
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
        logger.info(f'\n{df}')
        full_path = Path('bids_image_qc_information-customized.csv').absolute()
        df.to_csv(full_path, index=False)
        logger.info(f'CSV file written: {full_path}')
    elif args.ncanda is not None:
        args.ncanda
        df = ncanda_construct_data_frame(args.ncanda)
        logger.info(f'\n{df}')
        full_path = Path('ncanda0.csv').absolute()
        df.to_csv(full_path, index=False)
        logger.info(f'CSV file written: {full_path}')
    else:
        logger.info('Not enough arguments specified')
        logger.info(parser.format_help())
