import { vec3 } from 'gl-matrix';
import { VIEW_ORIENTATIONS } from '../vtk/constants';

class CrosshairSet {
  constructor(
    xyzName, ijkName, imageRepresentation,
    imageView, imageCanvas, iSlice, jSlice, kSlice,
  ) {
    this.xyzName = xyzName;
    this.ijkName = ijkName;
    this.imageRepresentation = imageRepresentation;
    this.imageData = this.imageRepresentation.getInputDataSet();
    this.imageView = imageView;
    this.renderer = this.imageView.getRenderer();
    this.renderWindow = this.imageView.getOpenglRenderWindow();
    this.imageCanvas = imageCanvas;
    this.iSlice = iSlice;
    this.jSlice = jSlice;
    this.kSlice = kSlice;
    this.ijkMapping = {
      x: 'i',
      y: 'j',
      z: 'k',
    };
  }

  getOrientation() {
    return this.imageRepresentation.getInputDataSet().getDirection();
  }

  getSliceLines() {
    const [iMax, jMax, kMax] = this.imageData.getDimensions();

    const iRepresentation = [
      [0, this.jSlice, this.kSlice],
      [iMax - 1, this.jSlice, this.kSlice],
    ];
    const jRepresentation = [
      [this.iSlice, 0, this.kSlice],
      [this.iSlice, jMax - 1, this.kSlice],
    ];
    const kRepresentation = [
      [this.iSlice, this.jSlice, 0],
      [this.iSlice, this.jSlice, kMax - 1],
    ];
    const [iPoints, jPoints, kPoints] = [iRepresentation, jRepresentation, kRepresentation].map(
      (representation) => [
        this.imageData.indexToWorld(representation[0]),
        this.imageData.indexToWorld(representation[1]),
      ].map(
        (point) => this.renderWindow.worldToDisplay(point[0], point[1], point[2], this.renderer)
          .map((c) => c / devicePixelRatio).slice(0, 2),
      ).map((point) => [point[0], this.imageCanvas.height - point[1]]),
    );
    return {
      i: {
        start: iPoints[0],
        end: iPoints[1],
      },
      j: {
        start: jPoints[0],
        end: jPoints[1],
      },
      k: {
        start: kPoints[0],
        end: kPoints[1],
      },
    };
  }

  getCrosshairsForAxis(axis, colors) {
    const sliceLines = this.getSliceLines();
    let horizontalLine = null;
    let verticalLine = null;
    if (axis === 'x') {
      horizontalLine = Object.assign(sliceLines.k, { color: colors.y });
      verticalLine = Object.assign(sliceLines.j, { color: colors.z });
    } else if (axis === 'y') {
      horizontalLine = Object.assign(sliceLines.k, { color: colors.x });
      verticalLine = Object.assign(sliceLines.i, { color: colors.z });
    } else if (axis === 'z') {
      horizontalLine = Object.assign(sliceLines.j, { color: colors.x });
      verticalLine = Object.assign(sliceLines.i, { color: colors.y });
    }

    return [horizontalLine, verticalLine];
  }

  findAxes() {
    const orientations = VIEW_ORIENTATIONS[this.xyzName];
    const signFlipVertical = Math.sign(orientations.viewUp.filter((v) => v !== 0)[0]);
    const upVector = orientations.viewUp;
    const leftVector = vec3.cross(
      [], orientations.viewUp, orientations.directionOfProjection,
    ).map((val) => val * signFlipVertical);
    const [verticalVectorIndex, horizontalVectorIndex] = [upVector, leftVector].map(
      (vector) => vector.findIndex((val) => val !== 0),
    );
    const [verticalAxisName, horizontalAxisName] = [verticalVectorIndex, horizontalVectorIndex].map(
      (index) => Object.values(this.ijkMapping)[index],
    );
    return [
      verticalAxisName,
      horizontalAxisName,
      verticalVectorIndex,
      horizontalVectorIndex,
    ];
  }

  ijkLocationOfClick(clickEvent) {
    const ijkLocation = {
      i: undefined,
      j: undefined,
      k: undefined,
    };
    const { layerX, layerY } = clickEvent;
    const { clientWidth, clientHeight } = this.imageView.getContainer();
    const [
      verticalAxisName,
      horizontalAxisName,
      verticalVectorIndex,
      horizontalVectorIndex,
    ] = this.findAxes();
    const horizontalFromCenter = layerX - (clientWidth / 2);
    const verticalFromCenter = (clientHeight / 2) - layerY;

    const worldCoordsClickLocation = this.renderWindow.displayToWorld(
      clientWidth / 2 + horizontalFromCenter,
      clientHeight / 2 + verticalFromCenter,
      0, this.renderer,
    );
    ijkLocation[horizontalAxisName] = worldCoordsClickLocation[horizontalVectorIndex];
    ijkLocation[verticalAxisName] = worldCoordsClickLocation[verticalVectorIndex];

    return ijkLocation;
  }
}

export default CrosshairSet;
