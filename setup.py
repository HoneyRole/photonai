from distutils.core import setup
from setuptools import find_packages
import photonai

setup(
  name='photonai',
  packages=find_packages(),
  include_package_data=True,
  version=photonai.__version__,
  description='A Python-Based Hyperparameter optimization Toolbox for Neural Networks',
  author='PHOTON Team',
  author_email='hahnt@wwu.de',
  url='https://github.com/photonai-team/photonai.git',
  download_url='https://github.com/photonai-team/photonai/archive/' + photonai.__version__ + '.tar.gz',
  keywords=['machine learning', 'deep learning', 'neural networks', 'hyperparameter'],
  classifiers=[],
  install_requires=[
        'numpy',
        'matplotlib',
        'progressbar2',
        'Pillow',
        'scikit-learn',
        'keras',
        'nilearn==0.5.0',
        'pandas',
        'nibabel',
        'pandas',
        'six',
        'h5py',
        'xlrd',
        'plotly',
        'imblearn',
        'pymodm==0.4.1',
        'scipy',
        'statsmodels',
        'flask',
        'prettytable',
        'scikit-optimize'
  ]
)
