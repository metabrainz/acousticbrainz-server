import requests
from flask import current_app

def get_messybrainz_id(querydata):
    """
    This function queries messybrainz to get a msid according to the 'artist/title' present in the item metadata
    Args:
        querydata: A dictionary containing basic info for one track
                   minimum fields required: [artis, song title]

    Returns:
        msid: string messybrainz id -> if it is found in the messybrainz database
        None: if no reference is fount in messybrainz database
    """
    if isinstance(querydata, dict):
        if 'artist' in querydata and 'title' in querydata:
            r = requests.post(current_app.config['MESSYBRAINZ_URL']+'submit', json=[querydata])
            r.raise_for_status()
            responsedata = r.json()
            ids = responsedata['payload'][0]['ids']
            if 'recording_mbid' in ids and 'recording_msid' in ids:
                if ids['recording_mbid'] != '':
                    msid = ids['recording_mbid']
                    id_type = 'mbid'
                elif ids['recording_msid'] != '':
                    msid = ids['recording_msid']
                    id_type = 'msid'
                else:
                    msid = None
            return msid, id_type
        else:
            raise ValueError('Incomplete Data: artist/title not present in input data')
    else:
        raise TypeError('Input data is not a dictionary')
