import logging
import math

import monai
from monai.transforms import Compose, EnsureChannelFirstd, LoadImaged, ScaleIntensityd, ToTensord
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error, r2_score
import torch
from torch.utils.data import DataLoader
import wandb

logger = logging.getLogger(__name__)

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


def get_model(file_path=None):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = TiledClassifier(
        in_shape=(1, 64, 64, 64),
        classes=regression_count + len(artifacts),
        channels=(4, 8, 16, 32, 64),
        strides=(2, 2, 2, 2, 2),
        dropout=0.1,
    )

    if file_path is not None:
        model.load_state_dict(torch.load(file_path, map_location=device))
        logger.info(f'Loaded NN model from file "{file_path}"')
    else:
        logger.info('NN model is initialized with random weights')

    model.to(device)

    return model


def get_image_transforms():
    itk_reader = monai.data.ITKReader()
    # Define transforms for image
    image_transforms = Compose(
        [
            LoadImaged(keys=['img'], reader=itk_reader),
            EnsureChannelFirstd(keys=['img']),
            ScaleIntensityd(keys=['img']),
            ToTensord(keys=['img']),
        ]
    )
    return image_transforms


def evaluate_model(model, data_loader, device, writer, epoch, run_name):
    model.eval()
    y_pred = []
    y_pred_continuous = []
    y_all = []
    y_true = []
    with torch.no_grad():
        metric_count = 0
        for val_data in data_loader:
            inputs = val_data['img'].to(device)
            info = val_data['info'].to(device)
            outputs = model(inputs)

            y_all.extend(outputs[..., :].cpu().tolist())
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
            logger.info(run_name + '_confusion_matrix:')
            logger.info(confusion_matrix(y_true, y_pred))
            logger.info(classification_report(y_true, y_pred))

            metric = mean_squared_error(y_true, y_pred_continuous, squared=False)
            writer.add_scalar(run_name + '_RMSE', metric, epoch + 1)
            wandb.log({run_name + '_RMSE': metric})
            metric = r2_score(y_true, y_pred_continuous)
            writer.add_scalar(run_name + '_R2', metric, epoch + 1)
            wandb.log({run_name + '_R2': metric})
            return metric
        else:
            return y_all


def evaluate1(model, image_path):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    evaluation_ds = monai.data.Dataset(
        data=[
            {
                'img': image_path,
                'info': torch.FloatTensor([0] * (regression_count + len(artifacts))),
            }
        ],
        transform=get_image_transforms(),
    )
    evaluation_loader = DataLoader(
        evaluation_ds, batch_size=1, pin_memory=torch.cuda.is_available()
    )

    output = evaluate_model(model, evaluation_loader, device, None, 0, 'evaluate1')
    result = output[0]
    logger.info(f'Network output: {result}')
    logger.info(f'Overall quality of {image_path}, on 0-10 scale: {result[0]:.1f}')

    labeled_results = {
        'overall_quality': result[0],
        'signal_to_noise_ratio': result[1],
        'contrast_to_noise_ratio': result[2],
    }
    for artifact_name, value in zip(artifacts, result[regression_count:]):
        labeled_results[artifact_name] = value
    return labeled_results


def evaluate_many(model, image_paths):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    evaluation_files = [
        {
            'img': image_path,
            'info': torch.FloatTensor([0] * (regression_count + len(artifacts))),
        }
        for image_path in image_paths
    ]

    evaluation_ds = monai.data.Dataset(evaluation_files, transform=get_image_transforms())
    evaluation_loader = DataLoader(evaluation_ds, pin_memory=torch.cuda.is_available())
    results = evaluate_model(model, evaluation_loader, device, None, 0, 'evaluate_many')

    labeled_results = {}
    for index, result in enumerate(results):
        corresponding_image_path = image_paths[index]
        single_labeled = {
            'overall_quality': result[0],
            'signal_to_noise_ratio': result[1],
            'contrast_to_noise_ratio': result[2],
        }
        for artifact_name, value in zip(artifacts, result[regression_count:]):
            single_labeled[artifact_name] = value
        labeled_results[corresponding_image_path] = single_labeled
    return labeled_results


if __name__ == '__main__':
    raise RuntimeError(
        'This file is not meant to be invoked by the user. Please invoke nn_training.py'
    )
