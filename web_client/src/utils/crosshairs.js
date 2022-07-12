import vtkCellPicker from 'vtk.js/Sources/Rendering/Core/CellPicker';

class CrosshairSet {
  constructor(
    xyzName, ijkName,
    imageRepresentation, imageView, imageCanvas,
    iSlice, jSlice, kSlice,
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

  trueAxis(axisName) {
    const xyzAxisOrdering = ['x', 'y', 'z'];
    const ijkAxisOrdering = ['i', 'j', 'k'];
    let axisOrdering = xyzAxisOrdering;
    if (ijkAxisOrdering.includes(axisName)) {
      axisOrdering = ijkAxisOrdering;
    }

    const axisNumber = axisOrdering.indexOf(axisName);
    const orientation = this.getOrientation();
    const axisOrientation = [
      orientation[axisNumber],
      orientation[3 + axisNumber],
      orientation[6 + axisNumber],
    ].map(
      (val) => Math.abs(val),
    );
    const trueAxis = axisOrdering[
      axisOrientation.indexOf(Math.max(...axisOrientation))
    ];
    return trueAxis;
  }

  getPicker() {
    const picker = vtkCellPicker.newInstance();
    picker.setPickFromList(1);
    picker.setTolerance(0);
    picker.initializePickList();
    picker.addPickList(this.imageRepresentation.getActors()[0]);
    return picker;
  }

  locationOfClick(clickEvent) {
    const picker = this.getPicker();
    picker.pick([clickEvent.position.x, clickEvent.position.y, 0], this.renderer);
    if (picker.getActors().length === 0) return { i: undefined, j: undefined, k: undefined };

    const [xyzLocation] = picker.getPickedPositions();
    const indexLocation = this.imageData.worldToIndex(xyzLocation);
    const halfDims = this.imageData.getDimensions().map((dim) => dim / 2);

    const worldCoords = Object.fromEntries(Object.entries({
      i: [indexLocation[0], halfDims[1], halfDims[2]],
      j: [halfDims[0], indexLocation[1], halfDims[2]],
      k: [halfDims[0], halfDims[1], indexLocation[2]],
    }).map(
      ([axis, coords]) => [axis, this.imageData.indexToWorld(coords)],
    ));

    const correctedAxes = Object.fromEntries(['i', 'j', 'k'].map((ijk) => [ijk, this.trueAxis(ijk)]));
    return {
      i: worldCoords[correctedAxes.i][0],
      j: worldCoords[correctedAxes.j][1],
      k: worldCoords[correctedAxes.k][2],
    };
  }
}

export default CrosshairSet;
