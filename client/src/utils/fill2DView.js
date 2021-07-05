export default function fill2DView(view) {
  view.resize();
  const viewName = view.getName();
  if (viewName === 'default') return;

  const bounds = view.getRenderer().computeVisiblePropBounds();
  const dim = [
    (bounds[1] - bounds[0]) / 2,
    (bounds[3] - bounds[2]) / 2,
    (bounds[5] - bounds[4]) / 2,
  ];
  const w = view.getContainer().clientWidth;
  const h = view.getContainer().clientHeight;
  const r = w / h;

  let x;
  let y;
  if (viewName === 'x') {
    [, x, y] = dim;
  } else if (viewName === 'y') {
    [x, , y] = dim;
  } else if (viewName === 'z') {
    [x, y] = dim;
  }
  if (r >= x / y) {
    // use width
    view.getCamera().setParallelScale(y + 1);
  } else {
    // use height
    view.getCamera().setParallelScale(x / r + 1);
  }
  view.resize();
}
