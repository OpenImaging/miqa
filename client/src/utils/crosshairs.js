class CrosshairSet {
  constructor(imageRepresentation, imageView, imageCanvas, iSlice, jSlice, kSlice) {
    this.imageRepresentation = imageRepresentation;
    this.imageView = imageView;
    this.imageCanvas = imageCanvas;
    this.iSlice = iSlice;
    this.jSlice = jSlice;
    this.kSlice = kSlice;
    this.colors = {
      i: '#fdd835',
      j: '#4caf50',
      k: '#b71c1c',
    };
  }

  getOrientation() {
    return this.imageRepresentation.getInputDataSet().getDirection();
  }

  getSliceLines() {
    const imageData = this.imageRepresentation.getInputDataSet();
    const [iMax, jMax, kMax] = imageData.getDimensions();
    const renderer = this.imageView.getRenderer();
    const renderWindow = this.imageView.getOpenglRenderWindow();

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
        imageData.indexToWorld(representation[0]),
        imageData.indexToWorld(representation[1]),
      ].map(
        (point) => renderWindow.worldToDisplay(point[0], point[1], point[2], renderer)
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

  getCrosshairsForAxis(axis) {
    const sliceLines = this.getSliceLines();
    let horizontalLine = null;
    let verticalLine = null;

    if (axis === 'x') {
      horizontalLine = Object.assign(sliceLines.k, { color: this.colors.j });
      verticalLine = Object.assign(sliceLines.j, { color: this.colors.k });
    } else if (axis === 'y') {
      horizontalLine = Object.assign(sliceLines.k, { color: this.colors.i });
      verticalLine = Object.assign(sliceLines.i, { color: this.colors.k });
    } else if (axis === 'z') {
      horizontalLine = Object.assign(sliceLines.j, { color: this.colors.i });
      verticalLine = Object.assign(sliceLines.i, { color: this.colors.j });
    }

    return [horizontalLine, verticalLine];
  }
}

export default CrosshairSet;
