import Mousetrap from 'mousetrap';
import _ from 'lodash';

function bind(el, value, bindElement) {
  const mousetrap = new Mousetrap(bindElement ? el : undefined);
  el.mousetrap = mousetrap;
  if (!_.isArray(value)) {
    value = [value];
  }
  value.forEach(({ bind: bind_, handler, disabled }) => {
    const handlerType = typeof handler;
    if (!disabled) {
      if (handlerType === 'function') {
        mousetrap.bind(bind_, (...params) => {
          handler.apply(this, [el, ...params]);
        });
      } else if (handlerType === 'object') {
        Object.keys(handler).forEach((eventType) => {
          const eventHandler = handler[eventType];
          mousetrap.bind(
            bind_,
            (...params) => {
              eventHandler.apply(this, [el, ...params]);
            },
            eventType,
          );
        });
      }
    }
  });
}

function unbind(el) {
  el.mousetrap.destroy();
}

export default function install(Vue) {
  Vue.directive('mousetrap', {
    inserted(el, { value, modifiers }) {
      bind(el, value, modifiers.element);
    },
    update(el, { value, modifiers }) {
      unbind(el);
      bind(el, value, modifiers.element);
    },
    unbind(el) {
      unbind(el);
    },
  });
}
