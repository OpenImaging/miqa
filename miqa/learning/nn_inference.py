import logging
import math

import itk
import monai
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, mean_squared_error, r2_score
import torch
from torch.utils.data import DataLoader
import torchio
import wandb

logger = logging.getLogger(__name__)

regression_count = 1  # use QA, ignore SNR and CNR
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
artifact_names = {
    artifact: (artifact if artifact != 'susceptibility_metal' else 'metal_susceptibility')
    for artifact in artifacts
}


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


# Matrices used to switch between LPS and RAS
FLIPXY_33 = np.diag([-1, -1, 1])
FLIPXY_44 = np.diag([-1, -1, 1, 1])


# taken from TorchIO and modified
# https://github.com/fepegar/torchio/blob/1bbf99e90cd06112c092a1fc227dedd5deb256ba/torchio/data/io.py#L344-L399
def get_ras_affine_from_sitk(sitk_object) -> np.ndarray:
    spacing = np.array(sitk_object.GetSpacing())
    direction_lps = np.array(sitk_object.GetDirection())
    origin_lps = np.array(sitk_object.GetOrigin())
    rotation_lps = direction_lps.reshape(3, 3)
    rotation_ras = np.dot(FLIPXY_33, rotation_lps)
    rotation_ras_zoom = rotation_ras * spacing
    translation_ras = np.dot(FLIPXY_33, origin_lps)
    affine = np.eye(4)
    affine[:3, :3] = rotation_ras_zoom
    affine[:3, 3] = translation_ras
    return affine


def get_rotation_and_spacing_from_affine(affine: np.ndarray):
    # From https://github.com/nipy/nibabel/blob/master/nibabel/orientations.py
    rotation_zoom = affine[:3, :3]
    spacing = np.sqrt(np.sum(rotation_zoom * rotation_zoom, axis=0))
    rotation = rotation_zoom / spacing
    return rotation, spacing


def get_sitk_metadata_from_ras_affine(
    affine: np.ndarray,
    is_2d: bool = False,
    lps: bool = True,
):
    direction_ras, spacing_array = get_rotation_and_spacing_from_affine(affine)
    origin_ras = affine[:3, 3]
    origin_lps = np.dot(FLIPXY_33, origin_ras)
    direction_lps = np.dot(FLIPXY_33, direction_ras)
    origin_array = origin_lps if lps else origin_ras
    direction_array = direction_lps if lps else direction_ras
    return origin_array, spacing_array, direction_array


class ReorientAndRescale(torchio.transforms.RescaleIntensity):
    def apply_transform(self, subject: torchio.Subject) -> torchio.Subject:
        # rescaling intensity first gives us a copy of the data
        transformed_subject = super().apply_transform(subject)

        np_array = transformed_subject.img.data
        assert np_array.shape[0] == 1  # we are dealing with scalar images
        np_array = np.squeeze(np_array, axis=0)  # remove channel dimension
        affine_matrix = subject['img'].affine

        # conversion of numpy ndarray + affine matrix into ITK image comes from:
        # https://gist.github.com/thewtex/9503448d2ad1dfacc2cbd620d95d3dac
        dimension = affine_matrix.shape[0] - 1
        assert dimension == 3
        itk_np_view = itk.image_view_from_array(np_array, is_vector=False)

        origin, spacing, direction = get_sitk_metadata_from_ras_affine(affine_matrix)
        itk_np_view.SetOrigin(origin)
        itk_np_view.SetSpacing(spacing)
        itk_np_view.SetDirection(direction)

        # reorient all images into DICOM LPS
        orient_filter = itk.OrientImageFilter.New(
            itk_np_view,
            use_image_direction=True,
            desired_coordinate_orientation=itk.SpatialOrientationEnums.ValidCoordinateOrientations_ITK_COORDINATE_ORIENTATION_RAI,
        )
        orient_filter.UpdateOutputInformation()

        # if original direction was not LPS, we need to run the filter and update the pixel data
        if np.any(orient_filter.GetOutput().GetDirection() != direction):
            orient_filter.Update()
            reoriented = orient_filter.GetOutput()
            # add channel dimension again
            np_reoriented = itk.array_from_image(reoriented)
            transformed_subject.img.data = np.expand_dims(np_reoriented, 0)
            transformed_subject['img'].affine = get_ras_affine_from_sitk(reoriented)

        return transformed_subject


def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)


def evaluate_model(model, data_loader, device, writer, epoch, run_name):
    model.eval()
    y_pred = []
    y_pred_continuous = []
    y_all = []
    y_true = []
    y_info = np.empty([0, 10])
    y_artifacts = np.empty([0, 10])
    with torch.no_grad():
        metric_count = 0
        for val_data in data_loader:
            inputs = val_data['img'][torchio.DATA].to(device)
            y_info1 = val_data['info'].numpy()[:, 1:]  # skip the overall QA
            y_info = np.concatenate((y_info, y_info1), axis=0)
            info = val_data['info'].to(device)
            outputs = model(inputs)

            y_all.extend(outputs[..., :].cpu().tolist())
            y_true.extend(info[..., 0].cpu().tolist())
            y = outputs[..., 0].cpu().tolist()
            y_pred_continuous.extend(y)
            y = [int(round(y[t])) for t in range(len(y))]
            y = [clamp(y[t], 0, 10) for t in range(len(y))]
            y_pred.extend(y)

            output_artifact = outputs[..., 1:].detach().cpu()
            y_a = output_artifact.numpy()
            y_a = np.rint(y_a)
            y_a = np.clip(y_a, 0, 1)
            y_artifacts = np.concatenate((y_artifacts, y_a), axis=0)

            metric_count += len(info)
            print('.', end='', flush=True)
            if metric_count % 100 == 0:
                print(metric_count, flush=True)

        if writer is not None:  # this is not a one-off case
            logger.info(f'{run_name}_confusion_matrix:\n{confusion_matrix(y_true, y_pred)}')
            logger.info(f'\n{classification_report(y_true, y_pred)}')

            logger.info(run_name + '_artifact_confusions [TN, FP, FN, TP]:')
            confusions = {}
            artifact_cm = []
            for a in range(len(artifacts)):
                y_a_true = y_info[:, a].tolist()
                y_a_out = y_artifacts[:, a].tolist()
                assert len(y_a_true) == len(y_a_out)

                for i in reversed(range(len(y_a_true))):
                    if y_a_true[i] == -1:  # ground truth was not provided
                        y_a_true.pop(i)
                        y_a_out.pop(i)
                cm = confusion_matrix(y_a_true, y_a_out)
                cm_list = list(np.concatenate(cm).flat)  # flatten into a list
                confusions[artifacts[a]] = cm_list
                artifact_cm.append(cm_list)
                logger.info(f'{artifacts[a]}: {cm_list}')
            logger.info(f'artifact_cm:\n{np.array(artifact_cm)}')

            metric = mean_squared_error(y_true, y_pred_continuous, squared=False)
            writer.add_scalar(run_name + '_RMSE', metric, epoch + 1)
            wandb.log({run_name + '_RMSE': metric})
            metric = r2_score(y_true, y_pred_continuous)
            writer.add_scalar(run_name + '_R2', metric, epoch + 1)
            wandb.log({run_name + '_R2': metric})
            return metric
        else:
            return y_all


def label_results(result):
    labeled_results = {'overall_quality': clamp(result[0] / 10.0, 0.0, 1.0)}
    for artifact_name, value in zip(artifacts, result[regression_count:]):
        result_name = artifact_names[artifact_name]
        result_value = clamp(value, 0.0, 1.0)
        if artifact_name not in ['normal_variants', 'full_brain_coverage']:
            result_name = 'no_' + result_name
            result_value = 1 - result_value
        labeled_results[result_name] = result_value
    return labeled_results


def evaluate1(model, image_path):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    rescale = ReorientAndRescale(out_min_max=(0, 1))

    evaluation_ds = monai.data.Dataset(
        data=[
            torchio.Subject(
                {
                    'img': torchio.ScalarImage(image_path),
                    'info': torch.FloatTensor([0] * (regression_count + len(artifacts))),
                }
            )
        ],
        transform=rescale,
    )
    evaluation_loader = DataLoader(
        evaluation_ds, batch_size=1, pin_memory=torch.cuda.is_available()
    )

    output = evaluate_model(model, evaluation_loader, device, None, 0, 'evaluate1')
    result = output[0]
    logger.info(f'Network output: {result}')
    logger.info(f'Overall quality of {image_path}, on 0-10 scale: {result[0]:.1f}')

    return label_results(result)


def evaluate_many(model, image_paths):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    evaluation_files = [
        torchio.Subject(
            {
                'img': torchio.ScalarImage(image_path),
                'info': torch.FloatTensor([0] * (regression_count + len(artifacts))),
            }
        )
        for image_path in image_paths
    ]

    rescale = ReorientAndRescale(out_min_max=(0, 1))
    evaluation_ds = monai.data.Dataset(evaluation_files, transform=rescale)
    evaluation_loader = DataLoader(evaluation_ds, pin_memory=torch.cuda.is_available())
    results = evaluate_model(model, evaluation_loader, device, None, 0, 'evaluate_many')

    labeled_results = {}
    for index, result in enumerate(results):
        labeled_results[image_paths[index]] = label_results(result)
    return labeled_results


if __name__ == '__main__':
    raise RuntimeError(
        'This file is not meant to be invoked by the user. Please invoke nn_training.py'
    )
