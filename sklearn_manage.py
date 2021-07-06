import click

from acousticbrainz.models.sklearn.model.classification_project import create_classification_project
from acousticbrainz.models.sklearn.model.predict import prediction

cli = click.Group()

@cli.command(name="classification_project")
@click.option("--ground-truth-file", "-g",
              help="Path of the dataset's groundtruth file/s.", required=True)
@click.option("--low-level-dir", "-d", required=True,
              help="Path of the main datasets dir containing .json file/s.")
@click.option("--project-file", "-f",
              help="Name of the project configuration file (.yaml) will be stored. If "
                   "not specified it takes automatically the name <project_CLASS_NAME>.")
@click.option("--export-path", "-o",
              help="Path where the project results will be stored. If empty, the results "
                   "will be saved in the main app directory.")
@click.option("--seed", "-s", type=int, default=None,
              help="Seed is used to generate the random shuffled dataset applied "
                   "later to folding.")
@click.option("--jobs", "-j", default=-1, type=int,
              help="Parallel jobs. Set to -1 to use all the available cores")
@click.option("--verbose", "-v", default=1, type=int,
              help="Controls the verbosity: the higher, the more messages.")
@click.option("--logging", "-l", default="INFO",
              type=click.Choice(
                  ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                  case_sensitive=False
              ), help="The logging level that will be printed")
def classification_project(ground_truth_file, low_level_dir, project_file, export_path,
                           seed, jobs, verbose, logging):
    """ Generates a project configuration file given a filelist, a groundtruth file,
    and the directories to store the datasets and the results files. The script has
    a parameter to specify the project template to use. If it is not specified, it
    will try to guess the appropriated one from the essentia version found on the
    descriptor files.
    """
    create_classification_project(
        ground_truth_file=ground_truth_file,
        dataset_dir=low_level_dir,
        project_file=project_file,
        exports_path=export_path,
        seed=seed,
        jobs=jobs,
        verbose=verbose,
        logging=logging
    )


@cli.command(name="predict")
@click.option("--project-file", "-f",  required=True,
              help="Name of the project configuration file (.yaml) that is to be loaded. "
                   "The .yaml at the end of the file is not necessary. Just put the name "
                   "of the file.")
@click.option("--export-path", "-o",
              help="Path where the project results will be stored. If empty, the results "
                   "will be saved in the main app directory.")
@click.option("--track", "-t", required=True,
              help="MBID of the the low-level data from the AcousticBrainz API.")
@click.option("--logging", "-l", default="INFO",
              type=click.Choice(
                  ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                  case_sensitive=False
              ), help="The logging level that will be printed")
def predict(project_file, export_path, track, logging):
    """ Prediction of a track. """
    prediction(
        exports_path=export_path,
        project_file=project_file,
        mbid=track,
        log_level=logging
    )


if __name__ == '__main__':
    cli()
