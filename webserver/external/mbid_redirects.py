import brainzutils.musicbrainz_db.exceptions as mb_exceptions
from mbdata import models


# Entity models
ENTITY_MODELS = {
    'recording': models.Recording,
}

# Redirect models
REDIRECT_MODELS = {
    'recording': models.RecordingGIDRedirect,
}


def get_entities_by_gids(query, entity_type, mbids):
    """Get entities using their MBIDs.
    An entity can have multiple MBIDs. This function may be passed another
    MBID of an entity, in which case, it is redirected to the original entity.
    Note that the query may be modified before passing it to this
    function in order to save queries made to the database.
    Args:
        query (Query): SQLAlchemy Query object.
        entity_type (str): Type of entity being queried.
        mbids (list): IDs of the target entities.
    Returns:
        Dictionary of objects of target entities keyed by their MBID.
    """
    entity_model = ENTITY_MODELS[entity_type]
    results = query.filter(entity_model.gid.in_(mbids)).all()
    remaining_gids = list(set(mbids) - {entity.gid for entity in results})
    entities = {str(entity.gid): entity for entity in results}
    if remaining_gids:
        redirect_model = REDIRECT_MODELS[entity_type]
        query = query.add_entity(redirect_model).join(redirect_model)
        results = query.filter(redirect_model.gid.in_(remaining_gids))
        for entity, redirect_obj in results:
            entities[redirect_obj.gid] = entity
        remaining_gids = list(set(remaining_gids) - {redirect_obj.gid for entity, redirect_obj in results})

    if remaining_gids:
        raise mb_exceptions.NoDataFoundException("Couldn't find entities with IDs: {mbids}".format(mbids=remaining_gids))
    
    return entities
