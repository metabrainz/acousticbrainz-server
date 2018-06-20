from __future__ import print_function

import click
from flask.cli import FlaskGroup

import db.mb_import
import dataset_eval.evaluate
import hl_extractor.hl_calc
import webserver

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command('hl_extractor')
@click.option('--threads', '-t', default=1, type=int)
def command_hl_extractor(threads=1):
    """Compute high-level features from low-level data files."""
    hl_extractor.hl_calc.main(threads)


@cli.command('dataset_evaluator')
def command_dataset_evaluator():
    """Evaluate pending datasets."""
    dataset_eval.evaluate.main()


@cli.command('musicbrainz_importer')
def command_musicbrainz_importer():
	"""Import MusicBrainz metadata"""
	db.mb_import.main()

if __name__ == '__main__':
    cli()
