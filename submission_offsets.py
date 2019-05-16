from flask.cli import FlaskGroup
import click
from collections import defaultdict

import db
import webserver

from sqlalchemy import text

cli = FlaskGroup(add_default_commands=False, create_app=webserver.create_app_flaskgroup)

@cli.command(name='add-offsets')
@click.option("--limit", "-l", default=10000)
def add_offsets(limit):
	"""Update lowlevel submission offsets with a specified limit."""
	incremental_add_offset(limit)

def incremental_add_offset(limit):
	with db.engine.connect() as connection:
		# Find the next batch of items to update
		batch_query = text("""
			SELECT id, gid
			  FROM lowlevel
			 WHERE submission_offset IS NULL
			 LIMIT :limit
		""")
		batch_result = connection.execute(batch_query, { "limit": limit })

		# Find max existing offsets
		offset_query = text("""
			SELECT gid, MAX(submission_offset)
			  FROM lowlevel
			 WHERE submission_offset IS NOT NULL
	      GROUP BY gid
		""")
		offset_result = connection.execute(offset_query)

		max_offsets = defaultdict(int)
		for gid, max_offset in offset_result.fetchall():
			max_offsets[gid] = max_offset

		print("Starting batch insertions...")
		print("============================")
		count = 0
		for id, gid in batch_result.fetchall():
			print("Finished {}/{} items".format(count, limit))
			print("Current lowlevel.id: {}".format(id)) 
			print("Inserting...")

			if gid in max_offsets:
				# Current offset exists
				max_offsets[gid] += 1
			else:
				# No existing offset
				max_offsets[gid] = 0
			offset = max_offsets[gid]

			query = text("""
				UPDATE lowlevel
				   SET submission_offset = :offset
				 WHERE id = :id
			""")
			connection.execute(query, { "id": id, "offset": offset })
			
			count += 1

		print("============================")
		print("Batch insertions finished.")


