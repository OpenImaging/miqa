<script lang="ts">
import { VRangeSlider } from 'vuetify/lib/components/VRangeSlider/';

export default VRangeSlider.extend({
  methods: {
    // override
    onSliderMouseDown(e) {
      if (e.target.classList.contains('v-slider__track-fill')) {
        this._middleDragStart = this.parseMouseMove(e);
      } else {
        this._middleDragStart = null;
      }
      VRangeSlider.options.methods.onSliderMouseDown.call(this, e);
    },
    // override
    onSliderClick() {
      // do nothing on click
    },
    // override
    onMouseMove(e) {
      const value = this.parseMouseMove(e);
      if (e.type === 'mousemove') {
        this.thumbPressed = true;
      }
      if (this._middleDragStart != null) {
        const delta = value - this._middleDragStart;
        this.applyRangeDelta(delta);
      } else {
        if (this.activeThumb === null) {
          this.activeThumb = this.getIndexOfClosestValue(
            this.internalValue,
            value,
          );
        }
        this.setInternalValue(value);
      }
    },
    // override
    applyRangeDelta(delta) {
      // this.oldValue is from VRangeSlider::onSliderMouseDown
      let [low, high] = this.oldValue;
      // assumption: min <= low < high <= max
      if (low + delta < this.min) {
        high -= low - this.min;
        low = this.min;
      } else if (high + delta > this.max) {
        low += this.max - high;
        high = this.max;
      } else {
        low += delta;
        high += delta;
      }
      this.internalValue = [low, high];
    },
  },
});
</script>

<style scoped>
.v-slider--horizontal .v-slider__track-container {
  height: 5px;
  display: flex;
  align-items: center;
}
.v-slider__track-fill:hover {
  cursor: grab;
}
</style>
