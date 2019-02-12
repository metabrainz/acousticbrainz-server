from __future__ import print_function
from flask.cli import FlaskGroup
import db
from db import dump
import click
import webserver

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)


@cli.command(name='show_failed_rows')
@click.option("--verbose", "-v", is_flag=True, help="Lists the details of failed rows.")
def show_failed_rows(verbose):
    """ Displays rows which do not contain highlevel metadata
    This command displays the following information about each failed row:

    1. Id : id of the failed row in highlevel table, 
    2. Mbid : Musicbrainz Identifier, 
    3. Offset : It is the position of the failed row in a set of rows
         having same mbids  
         (important if there have been more than 1 submission for an mbid
         so that we know which one to delete)
    """
    
    try:
       rows = db.data.show_failed_rows()
       failed_rows = len(rows)
       print("Number of highlevel rows that failed processing: ",failed_rows)
       if verbose and failed_rows:
           print("Id, Mbid, Offset")
           for row in rows:
               for id in row:
                    print(str(id)+", "+str(row[id][0])+", "+str(row[id][1]))
    
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)

@cli.command(name='remove_failed_rows')
def remove_failed_rows():
    """ Deletes rows which do not contain highlevel metadata
    """
    try:
       db.data.remove_failed_rows()
    except db.exceptions.DatabaseException as e:
        click.echo("Error: %s" % e, err=True)
        sys.exit(1)

