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
    const signFlipHorizontal = -1 * Math.sign(leftVector.filter((v) => v !== 0)[0]);
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
      signFlipVertical,
      signFlipHorizontal,
    ];
  }

  // findRenderWindowSize() {
  //   const { clientWidth, clientHeight } = this.imageView.getContainer();
  //   const sliceBounds = [[0, 0, 0], this.imageData.getDimensions()];
  //   const displayBounds = sliceBounds.map(
  //     ((sliceLocation) => this.imageData.indexToWorld(sliceLocation)),
  //   ).map((worldLocation) => this.renderWindow.worldToDisplay(
  //     ...worldLocation, this.renderer,
  //   ).map((c) => c / devicePixelRatio).slice(0, 2));
  //   const displayBoundsTranspose = displayBounds[0].map(
  //     (_, colIndex) => displayBounds.map((row) => row[colIndex]),
  //   );
  //   displayBoundsTranspose.forEach((row) => row.sort());

  //   const renderWindowWidth = Math.abs(
  //     Math.min(clientWidth, displayBoundsTranspose[0][1])
  //     - Math.max(0, displayBoundsTranspose[0][0]),
  //   );
  //   const renderWindowHeight = Math.abs(
  //     Math.min(clientHeight, displayBoundsTranspose[1][1])
  //     - Math.max(0, displayBoundsTranspose[1][0]),
  //   );
  //   return [renderWindowWidth, renderWindowHeight];
  //   // const horizontalRange = [
  //   //   Math.max(0, displayBounds[0][0]),
  //   //   Math.min(clientWidth, displayBounds[1][0]),
  //   // ];
  //   // const verticalRange = [
  //   //   Math.max(0, displayBounds[0][1]),
  //   //   Math.min(clientHeight, displayBounds[1][1]),
  //   // ];
  //   // console.log(horizontalRange, verticalRange);
  // }

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
      signFlipVertical,
      signFlipHorizontal,
    ] = this.findAxes();
    const horizontalFromCenter = layerX - (clientWidth / 2);
    const verticalFromCenter = (clientHeight / 2) - layerY + 5;
    // const [renderWindowWidth, renderWindowHeight] = this.findRenderWindowSize();

    // const displayLocation = [0, 0, 0];
    // displayLocation[horizontalVectorIndex] = clientWidth / 2 + horizontalFromCenter;
    // displayLocation[verticalVectorIndex] = clientHeight / 2 + verticalFromCenter;
    // console.log(displayLocation);
    const worldCoordsClickLocation = this.renderWindow.displayToWorld(
      clientWidth / 2 + horizontalFromCenter,
      clientHeight / 2 + verticalFromCenter,
      0, this.renderer,
    );
    console.log(worldCoordsClickLocation);
    ijkLocation[horizontalAxisName] = worldCoordsClickLocation[horizontalVectorIndex];
    ijkLocation[verticalAxisName] = worldCoordsClickLocation[verticalVectorIndex];

    // const sliceClickLocation = this.imageData.worldToIndex(
    //   worldCoordsClickLocation, [],
    // );
    // console.log([this.iSlice, this.jSlice, this.kSlice], '=>', sliceClickLocation);
    // const worldCoordsCenterFromSlice = this.imageData.indexToWorld(
    //   [this.iSlice, this.jSlice, this.kSlice], [],
    // );
    // const displayCenter = [0, 0, 0];
    // displayCenter[horizontalVectorIndex] = clientWidth / 2;
    // displayCenter[verticalVectorIndex] = clientHeight / 2;
    // const worldCoordsCenterFromDisplay = this.renderWindow.displayToWorld(
    //   clientWidth / 2, clientHeight / 2, 0, this.renderer,
    // );
    // console.log(worldCoordsCenterFromSlice, '=>', worldCoordsCenterFromDisplay);
    // const displayLocation = [0, 0, 0];
    // displayLocation[horizontalVectorIndex] = layerX;
    // displayLocation[verticalVectorIndex] = layerY;

    // console.log(displayLocation);
    // console.log(this.imageData.worldToIndex(
    //   this.renderWindow.displayToWorld(...displayLocation, this.renderer), [],
    // ));

    // console.log(horizontalFromCenter, verticalFromCenter);

    // const proportionFromLeft = (layerX - horizontalRange[0])
    // / (horizontalRange[1] - horizontalRange[0]);
    // let proportionFromTop = (layerY - verticalRange[0])
    // / (verticalRange[1] - verticalRange[0]);
    // if (signFlipVertical) {
    //   proportionFromTop = 1 - proportionFromTop;
    // }

    // const imageBounds = this.imageRepresentation.getBounds();
    // const [horMinSlice, horMaxSlice, vertMinSlice, vertMaxSlice] = [
    //   imageBounds[2 * horizontalVectorIndex],
    //   imageBounds[2 * horizontalVectorIndex + 1],
    //   imageBounds[2 * verticalVectorIndex],
    //   imageBounds[2 * verticalVectorIndex + 1],
    // ];

    // console.log(horMinSlice, horMaxSlice, vertMinSlice, vertMaxSlice);

    // const newHorSlice = horMinSlice + proportionFromLeft * (horMaxSlice - horMinSlice);
    // const newVertSlice = vertMinSlice + proportionFromTop * (vertMaxSlice - vertMinSlice);

    // console.log(proportionFromLeft, proportionFromTop);
    // console.log(newHorSlice, newVertSlice);

    // console.log('horizontal', proportionFromLeft * 100, '% between', horMinSlice, horMaxSlice, '=', newHorSlice);
    // console.log('vertical', proportionFromTop * 100, '% between', vertMinSlice, vertMaxSlice, '=', newVertSlice);

    // ijkLocation[horizontalAxisName] = newHorSlice;
    // ijkLocation[verticalAxisName] = newVertSlice;
    return ijkLocation;
  }
}

export default CrosshairSet;
