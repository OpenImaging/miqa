from pathlib import Path

from setuptools import find_packages, setup

readme_file = Path(__file__).parent / 'README.md'
if readme_file.exists():
    with readme_file.open() as f:
        long_description = f.read()
else:
    # When this is first installed in development Docker, README.md is not available
    long_description = ''

setup(
    name='miqa',
    version='0.1.0',
    description='',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    keywords='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python',
    ],
    python_requires='>=3.8',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'celery',
        'dateparser',
        'django>=3.2,<4.0',
        'django-allauth',
        'django-auth-style[allauth]',
        'django-configurations[database,email]',
        'django-extensions',
        'django-filter',
        'django-oauth-toolkit',
        'djangorestframework==3.13.1',  # https://github.com/axnsan12/drf-yasg/issues/810
        'django-click',
        'django-guardian',
        'drf-yasg',
        'pandas',
        'uri',
        # Production-only
        'django-composed-configuration[prod]',
        'django-s3-file-field[boto3]',
        'gunicorn',
        'schema',
    ],
    extras_require={
        'dev': [
            'django-composed-configuration[dev]',
            'django-debug-toolbar',
            'django-s3-file-field[minio]',
            'ipython',
            'tox',
            'django-click',
            'factory_boy',
            'girder-pytest-pyppeteer==0.0.9',
            'pytest-asyncio',
            'types-dateparser',
        ],
        'learning': [
            'itk>=5.3rc4',
            'monai',
            'sklearn',
            'torch',
            'torchio',
            'wandb',
        ],
        'zarr': [
            'itk-io',
            'itk-filtering',
            'spatial_image_ngff',
            'spatial_image_multiscale',
        ],
    },
)
