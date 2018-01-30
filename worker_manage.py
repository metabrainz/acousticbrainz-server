from __future__ import print_function

import click
from flask.cli import FlaskGroup

import dataset_eval.evaluate
import hl_extractor.hl_calc
import webserver

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app)


@cli.command('hl_extractor', help='High-level extractor tool')
@click.option('-t', default=1, type=int)
def command_hl_extractor(t=1):
    hl_extractor.hl_calc.main(t)


@cli.command('dataset_evaluator', help='Evaluate pending datasets')
def command_dataset_evaluator():
    dataset_eval.evaluate.main()


if __name__ == '__main__':
    cli()
