# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
from pathlib import Path
from sphinx.ext import apidoc

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
server_path = Path(__file__).parent.parent.parent
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
sys.path.insert(0, str(server_path))
sys.path.insert(1, str(Path(__file__).parent))

project = 'HockeyServerMinimap'
copyright = '2025, Rud356'
author = 'Rud356'
release = "0.0.2"
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

master_doc = 'index'
source_suffix = '.rst'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'docxbuilder'
]

templates_path = ['_templates']
exclude_patterns = ['_build', '**tests**', '**setup**', '**docs**', '**models**', '**static**', '**demo_inference.py**']

autodoc_member_order = 'bysource'

html_static_path = ['_static']
apidoc_module_dir = "./../"
apidoc_output_dir = './source/'
apidoc_separate_modules = True
apidoc_excluded_paths = ['tests', 'setup.py', 'post_install.py', '../server/demo_inference.py']
autodoc_default_flags = ['members']
autoclass_content = 'both'
autosummary_generate = True
add_module_names = False
class_members_toctree = False
html_show_sourcelink = False

language = 'ru'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

def setup(app):
    server_dir = '../server'
    if not on_rtd:
        apidoc.main([
            '-f', '-Var', '-E', '-M',
            '-o', './source/',
            server_dir,
        ])
