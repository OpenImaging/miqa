// eslint-disable-next-line import/prefer-default-export
export function cleanFrameName(name) {
  const cleanName = name.replace(/^image/, '').replace(/.nii.gz$/, '');
  if (cleanName === '') {
    return '1';
  }
  return cleanName;
}
