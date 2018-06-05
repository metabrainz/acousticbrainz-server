import db
from brainzutils import musicbrainz_db
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

def start_import():
    with db.engine.begin() as conn:
        lowlevel_query = text("""SELECT gid from lowlevel""")
        gids = conn.execute(lowlevel_query)
        gids_in_AB = gids.fetchall()
        for recording_gid in gids_in_AB:
            MB_artist_credit_data, MB_recording_data, MB_artist_data, MB_artist_type_data, MB_area_data, \
            MB_script_data, MB_release_data, MB_release_group_primary_type_data, MB_medium_data, \
            MB_track_data, MB_gender_data, MB_language_data, MB_medium_format_data, MB_release_group_data, \
            MB_release_status_data, MB_artist_gid_redirect_data, MB_recording_gid_redirect_data, \
            MB_release_group_gid_redirect_data, MB_release_gid_redirect_data, MB_artist_credit_name_data, \
            MB_area_type_data, MB_release_packaging_data = (0,)*22

            # FROM MUSICBRAINZ
            with musicbrainz_db.engine.begin() as connection:
                # ARTIST CREDIT
                try:
                    artist_credit_query = text("""SELECT artist_credit.id, artist_credit.name, artist_credit.artist_count,
                                                    artist_credit.ref_count, artist_credit.created
                                                    FROM artist_credit
                                                    INNER JOIN recording
                                                    ON artist_credit.id = recording.artist_credit
                                                    WHERE recording.gid= :recording_gid
                    """)
                    result = connection.execute(artist_credit_query, {"recording_gid" : recording_gid[0]})
                    MB_artist_credit_data = result.fetchall()
                except ValueError:
                    pass

                try:
                    artist_query = text("""
                        SELECT artist.id, artist.gid, artist.name, artist.sort_name, artist.begin_date_year,
                               artist.begin_date_month, artist.begin_date_day, artist.end_date_year, artist.end_date_month,
                               artist.end_date_day, artist.type, artist.area, artist.gender, artist.comment, artist.edits_pending,
                               artist.last_updated, artist.ended, artist.begin_area, artist.end_area
                          FROM artist
                    INNER JOIN artist_credit 
                            ON artist_credit.id = artist.id
                    INNER JOIN recording
                            ON artist_credit.id = recording.artist_credit
                    WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(artist_query, {"recording_gid": recording_gid[0]})
                    MB_artist_data = result.fetchall()
                except ValueError:
                    pass
                    
                # ARTIST TYPE
                try:
                    artist_type_query = text("""SELECT artist_type.id,
                                                        artist_type.name,
                                                        artist_type.parent,
                               artist_type.child_order,
                               artist_type.description,
                               artist_type.gid
                          FROM artist_type
                    INNER JOIN artist
                            ON artist.type = artist_type.id
                    INNER JOIN artist_credit
                            ON artist.id = artist_credit.id
                    INNER JOIN recording
                            ON artist_credit.id = recording.artist_credit
                         WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(artist_type_query, {"recording_gid": recording_gid[0]})
                    MB_artist_type_data = result.fetchall()
                except ValueError:
                    pass
                    
                # RECORDING
                try:
                    recording_query = text("""SELECT recording.id, recording.gid, recording.name, recording.artist_credit,
                                          recording.length, recording.comment, recording.edits_pending, recording.last_updated,
                                          recording.video
                                     FROM recording
                                    WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(recording_query, {"recording_gid": recording_gid[0]})
                    MB_recording_data = result.fetchall()
                except ValueError:
                    pass
                    
                # AREA
                try:
                    area_query = text("""
                        SELECT area.id,
                               area.gid,
                               area.name,
                               area.type,
                               area.edits_pending,
                               area.last_updated,
                               area.begin_date_year,
                               area.begin_date_month,
                               area.begin_date_day,
                               area.end_date_year,
                               area.end_date_month,
                               area.end_date_day,
                               area.ended, 
                               area.comment
                          FROM area
                    INNER JOIN artist
                            ON area.id = artist.area
                    INNER JOIN artist_credit
                            ON artist.id = artist_credit.id
                    INNER JOIN recording
                            ON artist_credit.id = recording.artist_credit
                         WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(area_query, {"recording_gid": recording_gid[0]})
                    MB_area_data = result.fetchall()
                except ValueError:
                    pass
                
                # BEGIN AREA
                try:
                    begin_area_query = text("""
                        SELECT area.id,
                               area.gid,
                               area.name,
                               area.type,
                               area.edits_pending,
                               area.last_updated,
                               area.begin_date_year,
                               area.begin_date_month,
                               area.begin_date_day,
                               area.end_date_year,
                               area.end_date_month,
                               area.end_date_day,
                               area.ended, 
                               area.comment
                          FROM area
                    INNER JOIN artist
                            ON area.id = artist.begin_area
                    INNER JOIN artist_credit
                            ON artist.id = artist_credit.id
                    INNER JOIN recording
                            ON artist_credit.id = recording.artist_credit
                         WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(begin_area_query, {"recording_gid": recording_gid[0]})
                    MB_begin_area_data = result.fetchall()
                except ValueError:
                    pass

                # END AREA
                try:
                    end_area_query = text("""
                        SELECT area.id,
                               area.gid,
                               area.name,
                               area.type,
                               area.edits_pending,
                               area.last_updated,
                               area.begin_date_year,
                               area.begin_date_month,
                               area.begin_date_day,
                               area.end_date_year,
                               area.end_date_month,
                               area.end_date_day,
                               area.ended, 
                               area.comment
                          FROM area
                    INNER JOIN artist
                            ON area.id = artist.end_area
                    INNER JOIN artist_credit
                            ON artist.id = artist_credit.id
                    INNER JOIN recording
                            ON artist_credit.id = recording.artist_credit
                         WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(end_area_query, {"recording_gid": recording_gid[0]})
                    MB_end_area_data = result.fetchall()
                except ValueError:
                    pass

                # AREA TYPE
                try:
                    area_type_query =   text("""SELECT area_type.id,
                                                       area_type.name,
                                                       area_type.parent,
                                                       area_type.child_order,
                                                       area_type.description,
                                                       area_type.gid
                                                  FROM area_type
                                            INNER JOIN area
                                                    ON area.type = area_type.id
                                            INNER JOIN artist
                                                    ON area.id = artist.area
                                            INNER JOIN artist_credit
                                                    ON artist.id = artist_credit.id
                                            INNER JOIN recording
                                                    ON artist_credit.id = recording.artist_credit
                                                 WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(area_type_query, {"recording_gid": recording_gid[0]})
                    MB_area_type_data = result.fetchall()
                except ValueError:
                    pass

                # BEGIN AREA TYPE
                try:
                    begin_area_type_query =   text("""SELECT area_type.id,
                                                       area_type.name,
                                                       area_type.parent,
                                                       area_type.child_order,
                                                       area_type.description,
                                                       area_type.gid
                                                  FROM area_type
                                            INNER JOIN area
                                                    ON area.type = area_type.id
                                            INNER JOIN artist
                                                    ON area.id = artist.begin_area
                                            INNER JOIN artist_credit
                                                    ON artist.id = artist_credit.id
                                            INNER JOIN recording
                                                    ON artist_credit.id = recording.artist_credit
                                                 WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(begin_area_type_query, {"recording_gid": recording_gid[0]})
                    MB_begin_area_type_data = result.fetchall()
                except ValueError:
                    pass

                # END AREA TYPE
                try:
                    end_area_type_query =   text("""SELECT area_type.id,
                                                       area_type.name,
                                                       area_type.parent,
                                                       area_type.child_order,
                                                       area_type.description,
                                                       area_type.gid
                                                  FROM area_type
                                            INNER JOIN area
                                                    ON area.type = area_type.id
                                            INNER JOIN artist
                                                    ON area.id = artist.end_area
                                            INNER JOIN artist_credit
                                                    ON artist.id = artist_credit.id
                                            INNER JOIN recording
                                                    ON artist_credit.id = recording.artist_credit
                                                 WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(end_area_type_query, {"recording_gid": recording_gid[0]})
                    MB_end_area_type_data = result.fetchall()
                except ValueError:
                    pass

                # ARTIST CREDIT NAME
                try:    
                    artist_credit_name_query = text("""SELECT artist_credit_name.artist_credit,
                                           artist_credit_name.position,
                                           artist_credit_name.artist,
                                           artist_credit_name.name,
                                           artist_credit_name.join_phrase
                                      FROM artist_credit_name
                                INNER JOIN artist_credit
                                        ON artist_credit_name.artist_credit = artist_credit.id
                                INNER JOIN recording
                                        ON artist_credit.id = recording.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(artist_credit_name_query, {"recording_gid": recording_gid[0]})
                    MB_artist_credit_name_data = result.fetchall()
                except ValueError:
                    pass

                # ARTIST GID REDIRECT
                try:
                    artist_gid_redirect_query = text("""SELECT artist_gid_redirect.gid,
                                           artist_gid_redirect.new_id,
                                           artist_gid_redirect.created
                                      FROM artist_gid_redirect
                                INNER JOIN artist
                                        ON artist.id = artist_gid_redirect.new_id
                                INNER JOIN artist_credit
                                        ON artist.id = artist_credit.id
                                INNER JOIN recording
                                        ON artist_credit.id = recording.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(artist_gid_redirect_query, {"recording_gid": recording_gid[0]})
                    MB_artist_gid_redirect_data = result.fetchall()
                except ValueError:
                    pass


                # GENDER
                try:
                    gender_query = text("""SELECT gender.id,
                                           gender.name,
                                           gender.parent,
                                           gender.child_order,
                                           gender.description,
                                           gender.gid
                                      FROM gender
                                INNER JOIN artist
                                        ON artist.gender = gender.id
                                INNER JOIN artist_credit
                                        ON artist.id = artist_credit.id
                                INNER JOIN recording
                                        ON artist_credit.id = recording.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(gender_query, {"recording_gid": recording_gid[0]})
                    MB_gender_data = result.fetchall()
                except ValueError:
                    pass

                # RELEASE
                try:
                    release_query = text("""SELECT release.id,
                                           release.gid,
                                           release.name,
                                           release.artist_credit,
                                           release.release_group,
                                           release.status,
                                           release.packaging,
                                           release.language,
                                           release.script,
                                           release.barcode,
                                           release.comment,
                                           release.edits_pending,
                                           release.quality,
                                           release.last_updated
                                      FROM release
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_query, {"recording_gid": recording_gid[0]})
                    MB_release_data = result.fetchall()
                except ValueError:
                    pass                  

                # LANGUAGE
                try:
                    language_query = text("""SELECT language.id,
                                           language.iso_code_2t,
                                           language.iso_code_2b,
                                           language.iso_code_1,
                                           language.name,
                                           language.frequency,
                                           language.iso_code_3
                                      FROM language
                                INNER JOIN release
                                        ON release.language = language.id
                                INNER JOIN recording
                                        ON recording.artist_credit=release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(language_query, {"recording_gid": recording_gid[0]})
                    MB_language_data = result.fetchall()
                except ValueError:
                    pass

                # MEDIUM
                try:
                    medium_query = text("""SELECT medium.id,
                                           medium.release,
                                           medium.position,
                                           medium.format,
                                           medium.name,
                                           medium.edits_pending,
                                           medium.last_updated,
                                           medium.track_count
                                      FROM medium
                                INNER JOIN release
                                        ON release.id = medium.release
                                INNER JOIN recording
                                        ON recording.artist_credit=release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(medium_query, {"recording_gid": recording_gid[0]})
                    MB_medium_data = result.fetchall()
                except ValueError:
                    pass

                # MEDIUM FORMAT
                try:
                    medium_format_query = text("""SELECT medium_format.id,
                                           medium_format.name,
                                           medium_format.parent,
                                           medium_format.child_order,
                                           medium_format.year,
                                           medium_format.has_discids,
                                           medium_format.description,
                                           medium_format.gid
                                      FROM medium_format
                                INNER JOIN medium
                                        ON medium_format.id = medium.format
                                INNER JOIN release
                                        ON release.id = medium.release
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(medium_format_query, {"recording_gid": recording_gid[0]})
                    MB_medium_format_data = result.fetchall()
                except ValueError:
                    pass

                # RECORDING GID REDIRECT
                try:    
                    recording_gid_redirect_query = text("""SELECT recording_gid_redirect.gid,
                                           recording_gid_redirect.new_id,
                                           recording_gid_redirect.created
                                      FROM recording_gid_redirect
                                INNER JOIN recording
                                        ON recording.id = recording_gid_redirect.new_id
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(recording_gid_redirect_query, {"recording_gid": recording_gid[0]})
                    MB_recording_gid_redirect_data = result.fetchall()
                except ValueError:
                    pass

                # release_gid_redirect
                try:    
                    release_gid_redirect_query = text("""SELECT release_gid_redirect.gid,
                                           release_gid_redirect.new_id,
                                           release_gid_redirect.created
                                      FROM release_gid_redirect
                                INNER JOIN release
                                        ON release.id = release_gid_redirect.new_id
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_gid_redirect_query, {"recording_gid": recording_gid[0]})
                    MB_release_gid_redirect_data = result.fetchall()
                except ValueError:
                    pass

                # release_group
                try:
                    release_group_query = text("""SELECT release_group.id,
                                                         release_group.gid,
                                                         release_group.name,
                                                         release_group.artist_credit,
                                                         release_group.type,
                                                         release_group.comment,
                                                         release_group.edits_pending,
                                                         release_group.last_updated
                                                    FROM release_group
                                              INNER JOIN recording
                                                      ON recording.artist_credit = release_group.artist_credit
                                                   WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_group_query, {"recording_gid": recording_gid[0]})
                    MB_release_group_data = result.fetchall()
                except ValueError:
                    pass

                # release_group gid redirect
                try:
                    release_group_gid_redirect_query = text("""SELECT release_group_gid_redirect.gid,
                                           release_group_gid_redirect.new_id,
                                           release_group_gid_redirect.created
                                      FROM release_group_gid_redirect
                                INNER JOIN release_group
                                        ON release_group.id = release_group_gid_redirect.new_id
                                INNER JOIN recording
                                        ON recording.artist_credit = release_group.artist_credit
                                     WHERE recording.gid = :recording_gid 
                    """)
                    result = connection.execute(release_group_gid_redirect_query, {"recording_gid": recording_gid[0]})
                    MB_release_group_gid_redirect_data = result.fetchall()
                except ValueError:
                    pass

                # release_group_primary_type
                try:    
                    release_group_primary_type_query = text("""SELECT release_group_primary_type.id, release_group_primary_type.name,
                                           release_group_primary_type.parent, release_group_primary_type.child_order,
                                           release_group_primary_type.description, release_group_primary_type.gid
                                    FROM release_group_primary_type INNER JOIN release_group 
                                    ON release_group_primary_type.id = release_group.type
                                    INNER JOIN recording
                                            ON recording.artist_credit = release_group.artist_credit
                                         WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_group_primary_type_query, {"recording_gid": recording_gid[0]})
                    MB_release_group_primary_type_data = result.fetchall()
                except ValueError:
                    pass

                # release_packaging
                try:    
                    release_packaging_query = text("""SELECT release_packaging.id,
                                           release_packaging.name,
                                           release_packaging.parent,
                                           release_packaging.child_order,
                                           release_packaging.description,
                                           release_packaging.gid
                                      FROM release_packaging
                                INNER JOIN release
                                        ON release.packaging = release_packaging.id
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_packaging_query, {"recording_gid": recording_gid[0]})
                    MB_release_packaging_data = result.fetchall()
                except ValueError:
                    pass

                # release_status
                try:        
                    release_status_query = text("""SELECT release_status.id,
                                           release_status.name,
                                           release_status.parent,
                                           release_status.child_order,
                                           release_status.description,
                                           release_status.gid
                                      FROM release_status
                                INNER JOIN release
                                        ON release.status = release_status.id
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(release_status_query, {"recording_gid": recording_gid[0]})
                    MB_release_status_data = result.fetchall()
                except ValueError:
                    pass

                # script
                try:
                    script_query = text("""SELECT script.id,
                                           script.iso_code,
                                           script.iso_number,
                                           script.name,
                                           script.frequency
                                      FROM script
                                INNER JOIN release
                                        ON release.script = script.id
                                INNER JOIN recording
                                        ON recording.artist_credit = release.artist_credit
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(script_query, {"recording_gid": recording_gid[0]})
                    MB_script_data = result.fetchall()
                except ValueError:
                    pass

                # track
                try:
                    track_query = text("""SELECT track.id,
                                           track.gid,
                                           track.recording,
                                           track.medium,
                                           track.position,
                                           track.number,
                                           track.name,
                                           track.artist_credit,
                                           track.length,
                                           track.edits_pending,
                                           track.last_updated,
                                           track.is_data_track
                                      FROM track
                                INNER JOIN recording
                                        ON track.recording = recording.id
                                     WHERE recording.gid = :recording_gid
                    """)
                    result = connection.execute(track_query, {"recording_gid": recording_gid[0]})
                    MB_track_data = result.fetchall()
                except ValueError:
                    pass


            # TO ACOUSTICBRAINZ
            with db.engine.connect() as connection:
                if MB_artist_credit_data:
                    for value in MB_artist_credit_data:
                        transaction = connection.begin()
                        try:
                            artist_credit_query = text("""
                                INSERT INTO musicbrainz.artist_credit
                                    VALUES (:id, :name, :artist_count, :ref_count, :created)""")
                            connection.execute(artist_credit_query, {"id" : value[0],
                                                                              "name" : value[1],
                                                                              "artist_count" : value[2],
                                                                              "ref_count" : value[3],
                                                                              "created" : value[4]
                            })
                            transaction.commit()
                            print("INSERTED artist_credit data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_artist_type_data:
                    for value in MB_artist_type_data:
                        transaction = connection.begin()
                        try:
                            artist_type_query = text("""
                                INSERT INTO musicbrainz.artist_type
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(artist_type_query, {"id":value[0],
                                                                            "name":value[1],
                                                                            "parent":value[2],
                                                                            "child_order":value[3],
                                                                            "description":value[4],
                                                                            "gid":value[5]
                            })
                            transaction.commit()
                            print("INSERTED artist_type data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_area_type_data:
                    for value in MB_area_type_data:
                        transaction = connection.begin()
                        try:
                            area_type_query = text("""
                                INSERT INTO musicbrainz.area_type
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(area_type_query, {"id": value[0],
                                                                            "name": value[1],
                                                                            "parent": value[2],
                                                                            "child_order": value[3],
                                                                            "description": value[4],
                                                                            "gid": value[5]})
                            transaction.commit()
                            print("INSERTED area_type data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()
                
                if MB_begin_area_type_data:
                    for value in MB_begin_area_type_data:
                        transaction = connection.begin()
                        try:
                            begin_area_type_query = text("""
                                INSERT INTO musicbrainz.area_type
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(begin_area_type_query, {"id": value[0],
                                                                            "name": value[1],
                                                                            "parent": value[2],
                                                                            "child_order": value[3],
                                                                            "description": value[4],
                                                                            "gid": value[5]})
                            transaction.commit()
                            print("INSERTED begin_area_type data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_end_area_type_data:
                    for value in MB_end_area_type_data:
                        transaction = connection.begin()
                        try:
                            end_area_type_query = text("""
                                INSERT INTO musicbrainz.area_type
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(end_area_type_query, {"id": value[0],
                                                                            "name": value[1],
                                                                            "parent": value[2],
                                                                            "child_order": value[3],
                                                                            "description": value[4],
                                                                            "gid": value[5]})
                            transaction.commit()
                            print("INSERTED end_area_type data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_status_data:
                    for value in MB_release_status_data:
                        transaction = connection.begin()
                        try:
                            release_status_query = text("""
                                INSERT INTO musicbrainz.release_status
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            result = connection.execute(release_status_query, {"id": value[0],
                                                                                "name":  value[1],
                                                                                "parent": value[2],
                                                                                "child_order": value[3],
                                                                                "description": value[4],
                                                                                "gid": value[5]})
                            transaction.commit()
                            print("INSERTED release_status data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_group_primary_type_data:
                    for value in MB_release_group_primary_type_data:
                        transaction = connection.begin()
                        try:
                            release_group_primary_type_query = text("""
                                INSERT INTO musicbrainz.release_group_primary_type
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(release_group_primary_type_query, {"id": value[0],
                                                                                            "name": value[1],
                                                                                            "parent": value[2],
                                                                                            "child_order": value[3],
                                                                                            "description": value[4],
                                                                                            "gid": value[5]})
                            transaction.commit()
                            print("INSERTED release_group_primary_type data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_medium_format_data:
                    for value in MB_medium_format_data:
                        transaction = connection.begin()
                        try:
                            medium_format_query = text("""
                                INSERT INTO musicbrainz.medium_format
                                    VALUES (:id, :name, :parent, :child_order, :year, :has_discids, :description, :gid)""")
                            connection.execute(medium_format_query, {"id": value[0], 
                                                                              "name": value[1],
                                                                              "parent": value[2],
                                                                              "child_order": value[3],
                                                                              "year": value[4],
                                                                              "has_discids": value[5],
                                                                              "description": value[6],
                                                                              "gid": value[7]})
                            transaction.commit()
                            print("INSERTED medium_format data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_packaging_data:
                    for value in MB_release_packaging_data:
                        transaction = connection.begin()
                        try:
                            release_packaging_query = text("""
                                INSERT INTO musicbrainz.release_packaging
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(release_packaging_query, {"id": value[0],
                                                                                  "name": value[1],
                                                                                  "parent": value[2],
                                                                                  "child_order": value[3],
                                                                                  "description": value[4],
                                                                                  "gid": value[5]})
                            transaction.commit()
                            print("INSERTED release_packaging data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_language_data:
                    for value in MB_language_data:
                        transaction = connection.begin()
                        try:
                            language_query = text("""
                                INSERT INTO musicbrainz.language
                                    VALUES (:iso_code_2t, :iso_code_2b, :iso_code_1, :name, :frequency, :iso_code_3)""")
                            connection.execute(language_query, {"iso_code_2t": value[0],
                                                                        "iso_code_2b": value[1],
                                                                        "iso_code_1": value[2], 
                                                                        "name": value[3],
                                                                        "frequency": value[4],
                                                                        "iso_code_3": value[5]})
                            transaction.commit()
                            print("INSERTED language data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_script_data:
                    for value in MB_script_data:
                        transaction = connection.begin()
                        try:
                            script_query = text("""
                                INSERT INTO musicbrainz.script
                                    VALUES (:id, :iso_code, :iso_number, :name, :frequency)""")
                            connection.execute(script_query, {"id": value[0],
                                                                       "iso_code": value[1],
                                                                       "iso_number": value[2],
                                                                       "name": value[3],
                                                                       "frequency": value[4]})
                            transaction.commit()
                            print("INSERTED script data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_gender_data:
                    for value in MB_gender_data:
                        transaction = connection.begin()
                        try:
                            gender_query = text("""
                                INSERT INTO musicbrainz.gender
                                    VALUES (:id, :name, :parent, :child_order, :description, :gid)""")
                            connection.execute(gender_query, {"id": value[0],
                                                              "name": value[1],
                                                              "parent": value[2],
                                                              "child_order": value[3],
                                                              "description": value[4],
                                                              "gid": value[5]})
                            transaction.commit()
                            print("INSERTED gender data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_area_data:
                    for value in MB_area_data:
                        transaction = connection.begin()
                        try:
                            area_query = text("""
                                INSERT INTO musicbrainz.area
                                    VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                                            :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                                            :ended, :comment)""")
                            connection.execute(area_query, {"id": value[0],
                                                                     "gid": value[1],
                                                                     "name": value[2],
                                                                     "type": value[3],
                                                                     "edits_pending": value[4],
                                                                     "last_updated": value[5],
                                                                     "begin_date_year": value[6],
                                                                     "begin_date_month": value[7],
                                                                     "begin_date_day": value[8],
                                                                     "end_date_year": value[9],
                                                                     "end_date_month": value[10],
                                                                     "end_date_day": value[11],
                                                                     "ended": value[12],
                                                                     "comment": value[13]})
                            transaction.commit()
                            print("INSERTED area data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_begin_area_data:
                    for value in MB_begin_area_data:
                        transaction = connection.begin()
                        try:
                            begin_area_query = text("""
                                INSERT INTO musicbrainz.area
                                    VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                                            :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                                            :ended, :comment)""")
                            connection.execute(begin_area_query, {"id": value[0],
                                                                     "gid": value[1],
                                                                     "name": value[2],
                                                                     "type": value[3],
                                                                     "edits_pending": value[4],
                                                                     "last_updated": value[5],
                                                                     "begin_date_year": value[6],
                                                                     "begin_date_month": value[7],
                                                                     "begin_date_day": value[8],
                                                                     "end_date_year": value[9],
                                                                     "end_date_month": value[10],
                                                                     "end_date_day": value[11],
                                                                     "ended": value[12],
                                                                     "comment": value[13]})
                            transaction.commit()
                            print("INSERTED begin_area data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_end_area_data:
                    for value in MB_end_area_data:
                        transaction = connection.begin()
                        try:
                            end_area_query = text("""
                                INSERT INTO musicbrainz.area
                                    VALUES (:id, :gid, :name, :type, :edits_pending, :last_updated, :begin_date_year,
                                            :begin_date_month, :begin_date_day, :end_date_year, :end_date_month, :end_date_day,
                                            :ended, :comment)""")
                            connection.execute(end_area_query, {"id": value[0],
                                                                     "gid": value[1],
                                                                     "name": value[2],
                                                                     "type": value[3],
                                                                     "edits_pending": value[4],
                                                                     "last_updated": value[5],
                                                                     "begin_date_year": value[6],
                                                                     "begin_date_month": value[7],
                                                                     "begin_date_day": value[8],
                                                                     "end_date_year": value[9],
                                                                     "end_date_month": value[10],
                                                                     "end_date_day": value[11],
                                                                     "ended": value[12],
                                                                     "comment": value[13]})
                            transaction.commit()
                            print("INSERTED end_area data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_artist_data:
                    for value in MB_artist_data:
                        transaction = connection.begin()
                        try:
                            artist_query = text("""
                              INSERT INTO musicbrainz.artist
                                  VALUES (:id, :gid, :name, :sort_name, :begin_date_year, :begin_date_month, :begin_date_day,
                                        :end_date_year, :end_date_month, :end_date_day, :type, :area, :gender, :comment, :edits_pending,
                                        :last_updated, :ended, :begin_area, :end_area)""")
                            connection.execute(artist_query, {"id": value[0],
                                                                       "gid": value[1],
                                                                       "name": value[2],
                                                                       "sort_name": value[3],
                                                                       "begin_date_year": value[4],
                                                                       "begin_date_month": value[5],
                                                                       "begin_date_day": value[6],
                                                                       "end_date_year": value[7],
                                                                       "end_date_month": value[8],
                                                                       "end_date_day": value[9],
                                                                       "type": value[10],
                                                                       "area": value[11],
                                                                       "gender": value[12], 
                                                                       "comment": value[13],
                                                                       "edits_pending": value[14],
                                                                       "last_updated": value[15],
                                                                       "ended": value[16],
                                                                       "begin_area": value[17],
                                                                       "end_area": value[18]})
                            transaction.commit()
                            print("INSERTED artist data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_artist_credit_name_data:
                    for value in MB_artist_credit_name_data:
                        transaction = connection.begin()
                        try:
                            artist_credit_name_query = text("""
                                INSERT INTO musicbrainz.artist_credit_name
                                    VALUES (:artist_credit, :position, :artist, :name, :join_phrase)""")
                            connection.execute(artist_credit_name_query, {"artist_credit": value[0],
                                                                          "position": value[1],
                                                                          "artist": value[2],
                                                                          "name": value[3],
                                                                          "join_phrase": value[4]})
                            transaction.commit()
                            print("INSERTED artist_credit_name data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_artist_gid_redirect_data:
                    for value in MB_artist_gid_redirect_data:
                        transaction = connection.begin()
                        try:
                            artist_gid_redirect_query = text("""
                                INSERT INTO musicbrainz.artist_gid_redirect
                                    VALUES (:gid, :new_id, :created)""")
                            connection.execute(artist_gid_redirect_query, {"gid": value[0],
                                                                            "new_id": value[1],
                                                                            "created": value[2]})
                            transaction.commit()
                            print("INSERTED artist_gid_redirect data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()


                if MB_recording_data:
                    for value in MB_recording_data:
                        transaction = connection.begin()
                        try:
                            recording_query = text("""
                                INSERT INTO musicbrainz.recording
                                    VALUES (:id, :gid, :name, :artist_credit, :length, :comment, :edits_pending, :last_updated, :video)""")
                            connection.execute(recording_query, {"id": value[0],
                                                                          "gid": value[1],
                                                                          "name": value[2],
                                                                          "artist_credit": value[3],
                                                                          "length": value[4],
                                                                          "comment": value[5],
                                                                          "edits_pending": value[6],
                                                                          "last_updated": value[7],
                                                                          "video": value[8]})
                            transaction.commit()
                            print("INSERTED recording data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_recording_gid_redirect_data:
                    for value in MB_recording_gid_redirect_data:
                        transaction = connection.begin()
                        try:
                            recording_gid_redirect_query = text("""
                                INSERT INTO musicbrainz.recording_gid_redirect
                                    VALUES (:gid, :new_id, :created)""")
                            connection.execute(recording_gid_redirect_query, {"gid": value[0],
                                                                                       "new_id": value[1],
                                                                                       "created": value[2]})
                            transaction.commit()
                            print("INSERTED recording_gid_redirect data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_group_data:
                    for value in MB_release_group_data:
                        transaction = connection.begin()
                        try:
                            release_group_query = text("""
                                INSERT INTO musicbrainz.release_group
                                    VALUES (:id, :gid, :name, :artist_credit, :type, :comment, :edits_pending, :last_updated)""")
                            connection.execute(release_group_query, {"id": value[0],
                                                                              "gid": value[1],
                                                                              "name": value[2],
                                                                              "artist_credit": value[3],
                                                                              "type": value[4],
                                                                              "comment": value[5],
                                                                              "edits_pending": value[6],
                                                                              "last_updated": value[7]})
                            transaction.commit()
                            print("INSERTED release_group data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_group_gid_redirect_data:
                    for value in MB_release_group_gid_redirect_data:
                        transaction = connection.begin()
                        try:
                            release_group_gid_redirect_query = text("""
                                INSERT INTO musicbrainz.release_group_gid_redirect
                                    VALUES (:gid, :new_id, :created)""")
                            connection.execute(release_group_gid_redirect_query, {"gid": value[0],
                                                                                           "new_id": value[1],
                                                                                           "created": value[2]})
                            transaction.commit()
                            print("INSERTED release_gid_redirect data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_data:
                    for value in MB_release_data:
                        transaction = connection.begin()
                        try:
                            release_query = text("""
                                INSERT INTO musicbrainz.release
                                    VALUES (:id, :gid, :name, :artist_credit, :release_group, :status, :packaging, :language,
                                            :script, :barcode, :comment, :edits_pending, :quality, :last_updated)""")
                            connection.execute(release_query, {"id": value[0],
                                                                        "gid": value[1],
                                                                        "name": value[2],
                                                                        "artist_credit": value[3],
                                                                        "release_group": value[4],
                                                                        "status": value[5],
                                                                        "packaging": value[6],
                                                                        "language": value[7],
                                                                        "script": value[8],
                                                                        "barcode": value[9],
                                                                        "comment": value[10],
                                                                        "edits_pending": value[11],
                                                                        "quality": value[12],
                                                                        "last_updated": value[13]})
                            transaction.commit()
                            print("INSERTED release data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_release_gid_redirect_data:
                    for value in MB_release_gid_redirect_data:
                        transaction = connection.begin()
                        try:
                            release_gid_redirect_query = text("""
                                INSERT INTO musicbrainz.release_gid_redirect
                                    VALUES (:gid, :new_id, :created)""")
                            connection.execute(release_gid_redirect_query, {"gid": value[0],
                                                                                           "new_id": value[1],
                                                                                           "created": value[2]})
                            transaction.commit()
                            print("INSERTED release_gid_redirect data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_medium_data:
                    for value in MB_medium_data:
                        transaction = connection.begin()
                        try:
                            medium_query = text("""
                                INSERT INTO musicbrainz.medium
                                    VALUES (:id, :release, :position, :format, :name, :edits_pending, :last_updated, :track_count)""")
                            connection.execute(medium_query, {"id": value[0],
                                                                       "release": value[1],
                                                                       "position": value[2],
                                                                       "format": value[3],
                                                                       "name": value[4],
                                                                       "edits_pending": value[5],
                                                                       "last_updated": value[6],
                                                                       "track_count": value[7]})
                            transaction.commit()
                            print("INSERTED medium data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

                if MB_track_data:
                    for value in MB_track_data:
                        transaction = connection.begin()
                        try:
                            track_query = text("""
                                INSERT INTO musicbrainz.track
                                    VALUES (:id, :gid, :recording, :medium, :position, :number, :name, :artist_credit, :length,
                                            :edits_pending, :last_updated, :is_data_track)""")
                            connection.execute(track_query, {"id": value[0],
                                                   "gid": value[1],
                                                   "recording": value[2],
                                                   "medium": value[3],
                                                   "position": value[4],
                                                   "number": value[5],
                                                   "name": value[6],
                                                   "artist_credit": value[7],
                                                   "length": value[8],
                                                   "edits_pending": value[9],
                                                   "last_updated": value[10],
                                                   "is_data_track": value[11]})
                            transaction.commit()
                            print("INSERTED track data\n")
                        except IntegrityError as e:
                            print(e.message)
                            transaction.rollback()

        print("--------------------------------DONE-----------------------------------")
