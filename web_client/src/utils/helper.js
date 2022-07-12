export default function formatSize(size, { base = 1024, unit = 'B' } = {}) {
  if (size < base) {
    return `${size} ${unit}`;
  }

  let i;
  let val = size;
  for (i = 0; val >= base && i < 4; i += 1) {
    val /= base;
  }

  return `${val.toFixed(2)}  ${['', 'K', 'M', 'G', 'T'][i]}${unit}`;
}
