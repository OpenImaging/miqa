import { VIEW_ORIENTATIONS, ANNOTATIONS } from './constants';

// ----------------------------------------------------------------------------

function getNumberOfVisibleViews(proxyManager) {
  let nbViews = 0;
  proxyManager.getViews().forEach((v) => {
    nbViews += v.getContainer() ? 1 : 0;
  });
  return nbViews;
}

// ----------------------------------------------------------------------------

function getViewActions(proxyManager) {
  const possibleActions = {
    crop: false,
  };

  // To crop we need at list an image data
  proxyManager.getSources().forEach((s) => {
    const ds = s.getFrame();
    if (ds && ds.isA && ds.isA('vtkImageData')) {
      possibleActions.crop = true;
    }
  });

  return possibleActions;
}

// ----------------------------------------------------------------------------

function getViewType(view) {
  return `${view.getProxyName()}:${view.getName()}`;
}

// ----------------------------------------------------------------------------

function getView(proxyManager, viewType) {
  const [type, name] = viewType.split(':');
  let view = null;
  const views = proxyManager.getViews();
  for (let i = 0; i < views.length; i += 1) {
    if (views[i].getProxyName() === type) {
      if (name) {
        if (views[i].getName() === name) {
          view = views[i];
        }
      } else {
        view = views[i];
      }
    }
  }

  if (!view) {
    view = proxyManager.createProxy('Views', type, { name });

    // Make sure represention is created for new view
    proxyManager
      .getSources()
      .forEach((s) => proxyManager.getRepresentation(s, view));

    // Update orientation
    //   LPS is the default of the view constructor
    //   Camera initialization when the view is rendered will override this
    //   with the project's preferred orientation
    const { axis, directionOfProjection, viewUp } = VIEW_ORIENTATIONS.LPS[name];
    view.updateOrientation(axis, directionOfProjection, viewUp);

    // set background to transparent
    view.setBackground(0, 0, 0, 0);

    // FIXME: Use storage to choose defaults
    view.setPresetToOrientationAxes('default');
  }

  return view;
}

// ----------------------------------------------------------------------------

function updateViewsAnnotation(proxyManager) {
  const hasImageData = proxyManager
    .getSources()
    .find((s) => s.getFrame().isA && s.getFrame().isA('vtkImageData'));
  const views = proxyManager.getViews();

  for (let i = 0; i < views.length; i += 1) {
    const view = views[i];
    view.setCornerAnnotation('se', '');
    if (view.getProxyName().indexOf('2D') !== -1 && hasImageData) {
      view.setCornerAnnotations(ANNOTATIONS, true);
    } else {
      view.setCornerAnnotation('nw', '');
    }
  }
}

// ----------------------------------------------------------------------------
export default {
  getViewType,
  getView,
  getViewActions,
  getNumberOfVisibleViews,
  updateViewsAnnotation,
};

export {
  getViewType,
  getView,
  getViewActions,
  getNumberOfVisibleViews,
  updateViewsAnnotation,
};
