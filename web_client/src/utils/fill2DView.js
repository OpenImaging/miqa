export default function fill2DView(view, w, h, resize = true) {
  if (!view) return undefined;
  if (resize) view.resize();
  const viewName = view.getName();
  if (viewName === 'default') return 0;

  const bounds = view.getRenderer().computeVisiblePropBounds();
  const dim = [
    (bounds[1] - bounds[0]) / 2,
    (bounds[3] - bounds[2]) / 2,
    (bounds[5] - bounds[4]) / 2,
  ];
  w = w || view.getContainer().clientWidth;
  h = h || view.getContainer().clientHeight;
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
  let scale;
  if (r >= x / y) {
    scale = y + 1;
  } else {
    scale = x / r + 1;
  }
  if (resize) {
    view.resize();
    view.getCamera().setParallelScale(scale);
  }
  return scale;
}
