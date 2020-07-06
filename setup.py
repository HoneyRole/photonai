try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

__version__ = '1.1.0'

setup(
    name='photonai',
    packages=find_packages(),
    include_package_data=True,
    version=__version__,
    description="""
PHOTON
is a rapid prototyping framework enabling (not so experienced) users to build, train, optimize, evaluate,
and share even complex machine learning pipelines with very high efficiency.

PHOTON is an object-oriented python framework designed to leave you deciding the important things and automatizing the rest:
 By treating each pipeline element as a building block, we create a system in which the user can select and combine
 processing steps, adapt their arrangement or stack them in more advanced pipeline layouts.

PHOTON gives you an easy way of setting up a full stack machine learning pipeline including nested cross-validation and hyperparameter search.
After PHOTON has found the best configuration for your model, it offers a convenient possibility to explore the analyzed hyperparameter space.
It also enables you to persist and load your optimal model, including all preprocessing elements, with only one line of code.

""",
    author='PHOTON Team',
    author_email='hahnt@wwu.de',
    url='https://github.com/photonai-team/photonai.git',
    download_url='https://github.com/photon-team/photonai/archive/' + __version__ + '.tar.gz',
    keywords=['machine learning', 'deep learning', 'neural networks', 'hyperparameter'],
    classifiers=[],
    install_requires=['numpy>=1.15.0',
                      'matplotlib',
                      'progressbar2',
                      'Pillow',
                      'scikit-learn>=0.21.3',
                      'keras',
                      'nilearn==0.5.0',
                      'pandas>=0.24.0',
                      'nibabel>=2.3.0',
                      'six',
                      'h5py',
                      'xlrd',
                      'plotly',
                      'imbalanced-learn>=0.7.0',
                      'pymodm==0.4.1',
                      'scipy==1.2',
                      'statsmodels',
                      'flask',
                      'prettytable',
                      'scikit-optimize>=0.5.2',
                      'scikit-image',
                      'seaborn',
                      'joblib>=0.13.2',
                      'fasteners',
                      'dask',
                      'distributed>=1.13.2']
)
